# Route Planner Backend
This documentation provides information on setting up, running, and understanding the backend of the Route Planner project. The service is implemented in Python using the FastAPI framework and is hosted on Azure.

## Technology Stack
- Python
- FastAPI
- MongoDB
- Firebase
- Google Maps API

## Running the app
1. Navigate to the projects directory in Windows CMD
2. Run `python -m venv env`
3. Enter the `./env` directory
4. Run `.\Scripts\activate`, you should see `(env)` at the beggining of the current line in terminal.
5. Run `pip install -r requirements.txt`
6. Create a new `.env` file in the `.\env` directory
7. Paste the required config values into the `.env` file
8. Navigate back to the projects main directory and run `uvicorn main:app --env-file ./env/.env`

## Running with expo
If you are running the UI Project locally using Expo Go or an Android Emulator, run the backend with `uvicorn` using the following options: `--host *your IPv4 address* --port *desired port*`. On windows your IPv4 address can be found using `ipconfig /all`.

## Documentation
Access the API documentation locally at [Docs on localhost](http://127.0.0.1:8000/docs).

## Configuration
In order to utilize the service, it is imperative to have multiple keys configured in the `.env` file. To obtain these keys, please direct message the Product Owner. It is crucial to refrain from sharing these sensitive data to maintain the security and integrity of the service.

## Dependencies
All required libraries and their versions are specified in the `requirements.txt` file.

## Project Structure
The project's architecture is organized with several folders, with two key directories playing pivotal roles in different functionalities:
- `routes` - handles all logic for route management
- `users` - manages user-related functionalities

## Testing
Tests are implemented using pytest. You can execute the unit tests for the app using `pytest -s`.
