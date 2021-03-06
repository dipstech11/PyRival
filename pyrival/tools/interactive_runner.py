import argparse
import asyncio
import shlex
import sys
from asyncio.subprocess import PIPE


async def tee(stream, streams, prefix):
    line = await stream.readline()
    while line.endswith(b'\n'):
        for s, p in zip(streams, prefix):
            s.write(p + line)
            if hasattr(s, 'flush'):
                s.flush()
        line = await stream.readline()

    if line:
        for s, p in zip(streams, prefix):
            s.write(p + line + b" % No new line\n")
            if hasattr(s, 'flush'):
                s.flush()


async def main(argv):
    parser = argparse.ArgumentParser(argv[0])
    parser.add_argument("program1")
    parser.add_argument("program2")
    parser.add_argument('--disable-stdout', default=False, action="store_true")
    parser.add_argument("--program1-stdout-prefix", default="Program 1 (stdout): ")
    parser.add_argument("--program1-stderr-prefix", default="Program 1 (stderr): ")
    parser.add_argument("--program2-stdout-prefix", default="Program 2 (stdout): ")
    parser.add_argument("--program2-stderr-prefix", default="Program 2 (stderr): ")

    args = parser.parse_args(argv[1:])

    process_1 = await asyncio.create_subprocess_exec(*shlex.split(args.program1), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    process_2 = await asyncio.create_subprocess_exec(*shlex.split(args.program2), stdin=PIPE, stdout=PIPE, stderr=PIPE)

    program1_stdout_prefix = args.program1_stdout_prefix.encode("utf-8")
    program1_stderr_prefix = args.program1_stderr_prefix.encode("utf-8")
    program2_stdout_prefix = args.program2_stdout_prefix.encode("utf-8")
    program2_stderr_prefix = args.program2_stderr_prefix.encode("utf-8")

    process_1_stdout_tee = [process_2.stdin]
    process_1_stdout_tee_prefixes = [b""]
    process_2_stdout_tee = [process_1.stdin]
    process_2_stdout_tee_prefixes = [b""]

    if not args.disable_stdout:
        process_1_stdout_tee.append(sys.stdout.buffer)
        process_1_stdout_tee_prefixes.append(program1_stdout_prefix)
        process_2_stdout_tee.append(sys.stdout.buffer)
        process_2_stdout_tee_prefixes.append(program2_stdout_prefix)

    await asyncio.gather(
        tee(process_1.stdout, process_1_stdout_tee, process_1_stdout_tee_prefixes),
        tee(process_2.stdout, process_2_stdout_tee, process_2_stdout_tee_prefixes),
        tee(process_1.stderr, [sys.stdout.buffer], [program1_stderr_prefix]),
        tee(process_2.stderr, [sys.stdout.buffer], [program2_stderr_prefix]),
    )

    print("Program 1 Exit Code:", await process_1.wait())
    print("Program 2 Exit Code:", await process_2.wait())


if __name__ == "__main__":
    asyncio.run(main(sys.argv))
