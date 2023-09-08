def show_progress(block_num: int, block_size: int, total_size: int) -> None:
    value = round(block_num * block_size / total_size * 100, 2)
    current_status = f"Downloaded {value}%."
    print(current_status, end="\r")
