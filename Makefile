serv:
	uvicorn main:cmd.app --reload
test:
	pytest -s
	# run tests via all ./* with test_ prefix
