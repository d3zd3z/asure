# Make for 'test'.

all:
	@echo Python is compiled on demand.

TESTS = $(wildcard t_*.py)
TESTS_RAN = $(patsubst %,%-passed,$(TESTS))
test sure: $(TESTS_RAN)

%.py-passed: %.py
	python $^
