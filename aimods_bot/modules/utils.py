

async def get_file(file):
    try:
        iter(file)
    except TypeError:
        return file.get_file()
    else:
        await get_file(file[-1])
