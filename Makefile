requirements.txt: setup.py
	pip-compile --generate-hashes  |  tee $@
	# Use pip-compile --upgrade  to update the packages


clean:
		rm -f *.pyc
