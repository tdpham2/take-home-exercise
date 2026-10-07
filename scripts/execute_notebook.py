"""Execute and save the notebook, optionally without local socket bindings."""
import argparse
import atexit
import asyncio
import json
import os
import signal
from contextlib import contextmanager
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]


@contextmanager
def cell_deadline(seconds):
    # In-process execute() itself is synchronous: queue timeouts alone cannot
    # interrupt a running cell. POSIX interval timers enforce the whole deadline.
    if not hasattr(signal, "setitimer"):
        raise RuntimeError("In-process deadlines require POSIX timers; use the standard nbclient execution method.")
    def expired(*_):
        raise TimeoutError(f"Notebook cell exceeded {seconds} seconds")
    previous_handler = signal.signal(signal.SIGALRM, expired)
    previous_timer = signal.setitimer(signal.ITIMER_REAL, seconds)
    try:
        yield
    finally:
        signal.setitimer(signal.ITIMER_REAL, *previous_timer)
        signal.signal(signal.SIGALRM, previous_handler)


def in_process(nb, cell_timeout=300):
    from ipykernel.inprocess.manager import InProcessKernelManager
    from traitlets.config import Config
    km = InProcessKernelManager(config=Config({"HistoryManager": {"hist_file": ":memory:", "enabled": False}}))
    km.start_kernel()
    kc = km.client()
    kc.start_channels()
    try:
        for position, cell in enumerate(nb["cells"]):
            if cell["cell_type"] != "code":
                continue
            cell["outputs"] = []
            source = cell["source"]
            source = "".join(source) if isinstance(source, list) else source
            with cell_deadline(cell_timeout):
                mid = kc.execute(source)
                reply = kc.get_shell_msg(timeout=cell_timeout)
                cell["execution_count"] = reply["content"]["execution_count"]
                while True:
                    message = kc.get_iopub_msg(timeout=cell_timeout)
                    parent_id = message.get("parent_header", {}).get("msg_id")
                    # ipykernel 7's in-process stdout messages may lack a parent
                    # header. Execution here is strictly sequential, so those
                    # stream messages belong to the currently executing cell.
                    if parent_id != mid and not (not parent_id and message["msg_type"] == "stream"):
                        continue
                    kind = message["msg_type"]
                    if kind in {"stream", "display_data", "execute_result", "error"}:
                        fields = {"stream": ["name", "text"], "display_data": ["data", "metadata"],
                                  "execute_result": ["data", "metadata", "execution_count"],
                                  "error": ["ename", "evalue", "traceback"]}[kind]
                        cell["outputs"].append({"output_type": kind, **{k: message["content"][k] for k in fields}})
                    elif kind == "clear_output":
                        cell["outputs"].clear()
                    elif kind == "status" and message["content"]["execution_state"] == "idle":
                        break
            if reply["content"]["status"] != "ok" or any(o["output_type"] == "error" for o in cell["outputs"]):
                raise RuntimeError(f"Notebook cell {position} failed: {reply['content'].get('ename')}: {reply['content'].get('evalue')}")
            print(f"Executed code cell {cell['execution_count']}", flush=True)
        nb["metadata"]["task1_execution"] = {"method": "in-process ipykernel", "reason": "local sockets unavailable in managed environment"}
    finally:
        kc.stop_channels()
        atexit.unregister(km.kernel.shell.atexit_operations)
        km.kernel.shell.atexit_operations()
        async def drain():
            pending = [task for task in asyncio.all_tasks() if task is not asyncio.current_task()]
            for task in pending:
                task.cancel()
            await asyncio.gather(*pending, return_exceptions=True)
        # Await ipykernel's event-pipe cleanup before stopping its I/O thread.
        asyncio.run_coroutine_threadsafe(drain(), km.kernel.iopub_thread.io_loop.asyncio_loop).result(timeout=5)
        km.shutdown_kernel()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--in-process", action="store_true", help="Use a real IPython/Jupyter kernel in the current process; no sockets")
    parser.add_argument("--notebook", default="task1_memory.ipynb", help="Notebook path relative to the project root")
    parser.add_argument("--cell-timeout", type=int, default=int(os.getenv("MEMORY_NOTEBOOK_CELL_TIMEOUT", "300")),
                        help="Maximum seconds for each cell in either execution method")
    args = parser.parse_args()
    if args.cell_timeout < 1:
        parser.error("--cell-timeout must be positive")
    path = ROOT / args.notebook
    nb = json.loads(path.read_text())
    os.chdir(ROOT)
    os.environ["PYDEVD_DISABLE_FILE_VALIDATION"] = "1"
    with TemporaryDirectory(prefix="kep-notebook-ipython-") as profile:
        os.environ["IPYTHONDIR"] = profile
        if args.in_process:
            in_process(nb, args.cell_timeout)
        else:
            import nbformat
            from nbclient import NotebookClient
            nb = nbformat.from_dict(nb)
            nbformat.validate(nb)
            NotebookClient(nb, timeout=args.cell_timeout, kernel_name="python3", resources={"metadata": {"path": str(ROOT)}}).execute()
            nb.metadata["task1_execution"] = {"method": "nbclient fresh kernel"}
    nb["metadata"]["task1_execution"]["cell_timeout_seconds"] = args.cell_timeout
    assert not any(o["output_type"] == "error" for c in nb["cells"] if c["cell_type"] == "code" for o in c["outputs"])
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False) + "\n")
    print(f"Executed {sum(c['cell_type'] == 'code' for c in nb['cells'])} code cells with no errors: {path.name}")


if __name__ == "__main__":
    main()
