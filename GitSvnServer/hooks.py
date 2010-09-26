
def pre_commit(exitcode, errstr):
    msg = "Commit blocked by pre-commit hook (exit code %d) with " % exitcode
    if errstr is None or errstr == "":
        msg += "no output."
    else:
        msg += "output:\n%s" % errstr
    return 165001, msg
