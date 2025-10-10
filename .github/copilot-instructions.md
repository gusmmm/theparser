# python
- this project is written in python 3.13
- always use `uv`to manage environments, dependencies and run scripts
- use icecream to debug and logging
- use rich to print tables and progress bars
- use colorama to colorize terminal output
- always annotate the code
- always create rich output to the terminal

# annotations
- use yaml for annotations
- always annotate functions and classes
- always annotate the return type of functions and methods
- always annotate variables
- use the project structure to find the right place to put the code

# llamaindex and llamaparse
- use llamaparse to parse documents

# reports
- use pandas to generate reports
- use matplotlib to plot reports
- all the reports are generated in the reports/ folder

# google-genai sdk api
- always use the latest documentation at https://ai.google.dev/gemini-api/docs before implementing anything related to google-genai clients
- use thinking budget if necessary, see at https://ai.google.dev/gemini-api/docs/thinking how to use it
- use structured output using pydantic models, see at https://ai.google.dev/gemini-api/docs/structured-output how to use it.
- always use the `gemini-2.5-flash` model for all tasks, unless specified otherwise

# database
- use a local mongodb database for all the data storage
- use pymongo to interact with the database
- always create indexes for the collections to optimize queries
- the code to interact with the database is in the database/ folder