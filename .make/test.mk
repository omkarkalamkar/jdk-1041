# Unit test command
unit-test:
	chmod 755 run_tox.sh; \
	./run_tox.sh;

# Lint command
lint:
	chmod 755 run_lint.sh; \
	./run_lint.sh;