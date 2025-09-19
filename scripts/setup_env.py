"""Create a local .env from .env.example and generate missing Fernet keys.

Usage:
  python scripts/setup_env.py         # interactively creates .env if missing
  python scripts/setup_env.py --force # overwrite existing .env
"""
import os
import argparse
from cryptography.fernet import Fernet


def generate_key():
    return Fernet.generate_key().decode()


def load_example(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"{path} not found")
    with open(path, 'r', encoding='utf-8') as f:
        return f.read()


def create_env_from_example(example_text, force=False):
    env_path = os.path.join(os.getcwd(), '.env')
    if os.path.exists(env_path) and not force:
        print('.env already exists. Use --force to overwrite.')
        return

    # Parse lines and fill keys
    out_lines = []
    for line in example_text.splitlines():
        if line.strip().startswith('DB_ENCRYPTION_KEY='):
            out_lines.append('DB_ENCRYPTION_KEY=' + generate_key())
        elif line.strip().startswith('USER_DATA_ENCRYPTION_KEY='):
            out_lines.append('USER_DATA_ENCRYPTION_KEY=' + generate_key())
        else:
            out_lines.append(line)

    with open(env_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(out_lines) + '\n')

    print(f'Created {env_path} with generated keys (local only).')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true', help='Overwrite existing .env')
    args = parser.parse_args()

    example_path = os.path.join(os.getcwd(), '.env.example')
    try:
        example_text = load_example(example_path)
    except FileNotFoundError:
        print('Could not find .env.example in the repo root. Create one first.')
        return

    create_env_from_example(example_text, force=args.force)


if __name__ == '__main__':
    main()
