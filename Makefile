serv:
	uvicorn main:app --reload
test:
	pytest -s
	# run tests via all ./* with test_ prefix
