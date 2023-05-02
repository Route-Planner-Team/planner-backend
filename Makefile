serv:
	uvicorn main:app --reload
test:
	pytest
	# run tests via all ./* with test_ prefix
	