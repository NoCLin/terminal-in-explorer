import argparse
import os
import sys


def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("command",default="run",nargs="?")
    parser.add_argument("-d", "--debug",action="store_true")
    args = parser.parse_args()

    if not args.debug:
        os.environ["PYSNOOPER_DISABLED"] = "True"

    import tie.main
    import tie.register

    if args.command == "run":
        sys.exit(tie.main.main())
    if args.command == "register":
        sys.exit(tie.register.main(True))
    elif args.command == "unregister":
        sys.exit(tie.register.main(False))
    else:
        print("Unknown command: " + args.command)
        exit()


if __name__ == "__main__":

    main()
