

def expected_file_name(filename):
    """Returns true if a filename matches an expected bag name

    Expected bag names are 32 characters before a file extension, and have a file extension of .tar or .tar.gz

    Args:
        filename (string): a filename (not including full path)

    Returns:
        boolean: True if filename matches, false otherwise"""
    filename_split = filename.split(".")
    if len(filename_split[0]) == 32 and filename_split[-1] in ["tar", "tgz", "gz"]:
        return True
    else:
        return False
