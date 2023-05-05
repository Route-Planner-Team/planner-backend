# planner-backend

author setup: Python3.9

```
  - python3 -m venv env
  - source env/bin/activate
  - pip install -r requirements.txt
  - create .env file and put MONGO=abc
  Where abc must be mongoDB connection string(write me DM to get it)
  - make serv 
  starts local server on localhost 8000

```
  Docs avalible here: [Docs on localhost](http://127.0.0.1:8000/docs).

## Running with expo
If you are running the UI Project locally using Expo Go or an Android Emulator, run the backend with `uvicorn` using the following options: `--host *your IPv4 address* --port *desired port*`. On windows your IPv4 address can be found using `ipconfig /all`.

## Running on windows
1. Navigate to the projects directory in Windows CMD
2. Run `python -m venv env`
3. Enter the `./env` directory
4. Run `.\Scripts\activate`, you should see `(env)` at the beggining of the current line in terminal.
5. Run `pip install -r requirements.txt`
6. Create a new `.env` file in the `.\env` directory
7. Paste the required config values into the `.env` file
8. Navigate back to the projects main directory and run `uvicorn main:app --env-file ./env/.env`