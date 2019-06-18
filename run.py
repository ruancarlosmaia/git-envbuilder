import sys
import eventlet

eventlet.monkey_patch()

# Import application modules
from app import config

# CLI Command configuration
from app import cli

# Executes the application
if __name__ == '__main__': cli()