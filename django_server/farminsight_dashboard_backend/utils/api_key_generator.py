import random
import string


def generate_random_api_key(length=32):
    # Define the characters to include: letters, digits, and special characters
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"

    return ''.join(random.choice(characters) for _ in range(length))


def generate_random_token(length=32):
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))