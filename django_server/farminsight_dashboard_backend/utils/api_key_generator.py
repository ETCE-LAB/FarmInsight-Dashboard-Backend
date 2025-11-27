import logging
import random
import string

logger = logging.getLogger(__name__)


def generate_random_api_key(length=32):
    # Define the characters to include: letters, digits, and special characters
    logger.info("Generating new random API key.")
    characters = string.ascii_letters + string.digits + "!@#$%^&*()-_=+"

    return ''.join(random.choice(characters) for _ in range(length))


def generate_random_token(length=32):
    logger.info("Generating new random token.")
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))
