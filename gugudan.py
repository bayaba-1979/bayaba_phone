def print_gugudan():
    """Print the Korean multiplication table (구구단) from 2 to 9."""
    for dan in range(2, 10):
        for num in range(1, 10):
            print(f"{dan} x {num} = {dan * num:2d}")
        print()  # blank line between each dan


if __name__ == "__main__":
    print_gugudan()
