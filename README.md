# Parnassius

Parnassius is a [Discord](https://discordapp.com/) bot for the [University of Warwick Computing Society](https://uwcs.co.uk).
It handles moderation actions on the server.

Parnassius stems from [Apollo](https://github.com/UWCS/apollo), a general purpose bot.
It was named after the *[Parnassius autocrator](https://en.wikipedia.org/wiki/Parnassius_autocrator)*, a species of butterfly in the *Parnassius* genus.
Members of the *Parnassius* genus are known as Apollos, and autocrator refers to an individual who is unrestrained by superiors.

## Installation

Parnassius is built and tested against Python 3.8.

### Dependencies

Two type of dependency files are included with this project. The first, `requirements.txt`, only includes top-level dependencies.

The second, `requirements-platform.lock`, contains a pinned list of all dependencies specific to a platform.

If installing the top-level dependencies does not work, try installing the pinned dependencies.

### Environment Setup

1. Create a new virtual environment.  
   `python -m venv .venv`
2. Activate the virtual environment
    - On Linux and macOS: `source .venv/bin/activate`.
    - On Windows: `.\.venv\Scripts\activate`.
3. Confirm the virtual environment has been activated.
    - On Linux and macOS: `which python`.  
      Expected output: `.../.venv/bin/python`.
    - On Windows: `where.exe python`.  
      Expected output: `...\.venv\Scripts\python.exe`.
4. Install dependencies.  
    `pip install -r requirements.txt`.
5. Create the following configuration files (by copying them and configuring their fields) from the included examples:
    - `config.example.yaml` to `config.yaml`.
    - `alembic.example.ini` to `alembic.ini`.
    - `resources/discord_logging.example.yaml` to `discord_logging.yaml`.
7. Create a database for Parnassius to run on.  
    On postgres:
    - `CREATE USER parnassius WITH PASSWORD 'parnassius';`
    - `CREATE DATABASE parnassius WITH ONWER = parnassius;`
8. Prepare the database by running migrations with `alembic upgrade head`.
9. On the [Discord developer portal](https://discord.com/developers/) ensure your application has the required intents.
    - Parnassius requires the Server Members intent.
    
## Running 

Run `parnassius.py`, either through `python3 parnassius.py` or by executing the file.

## Contributor Notes

- Before committing run `isort .` and `black .` to ensure a consistent code style across Parnassius.
- Errors installing Psycopg are likely due to missing dependencies to compile the library.
  It requires the `Python.h` header file, typically provided by a package called `python3-dev`.
  It also requires `libpq-fe.h`, typically contained in `libpq-dev`.
    - Alternately, it can be replaced with `psycopg-binary`.
