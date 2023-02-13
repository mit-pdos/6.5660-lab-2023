ASFLAGS   := -m64
CFLAGS    := -m64 -g -std=c99 -Wall -Wno-format-overflow -D_GNU_SOURCE -static
LDFLAGS   := -m64
LDLIBS    := 
PROGS     := zookd zookd-exstack zookd-nxstack zookd-withssp shellcode.bin run-shellcode
ifneq (,$(wildcard zookfs.c zookd2.c))
PROGS     += zookfs zookd2
endif
SHELLCODE := $(patsubst %.S,%.bin,$(wildcard shellcode*.S))

all: $(PROGS)
.PHONY: all

zookd zookd2 zookfs: %: %.o http.o
zookd-exstack: %-exstack: %.o http.o
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@ -z execstack
zookd-nxstack: %-nxstack: %.o http.o
	$(CC) $(LDFLAGS) $^ $(LOADLIBES) $(LDLIBS) -o $@
zookd-withssp: %: %.o http-withssp.o
run-shellcode: %: %.o

%.o: %.c
	$(CC) $< -c -o $@ $(CFLAGS) -fno-stack-protector
.PRECIOUS: %.o

%-withssp.o: %.c
	$(CC) $< -c -o $@ $(CFLAGS)
.PRECIOUS: %-withssp.o

%.bin: %.o
	objcopy -S -O binary -j .text $< $@

.PHONY: check-crash
check-crash: bin.tar.gz $(SHELLCODE)
	./check-bin.sh
	tar xf bin.tar.gz
	for f in ./exploit-2*.py; do ./check-crash.sh zookd-exstack $$f; done

.PHONY: check-exstack
check-exstack: bin.tar.gz $(SHELLCODE)
	./check-bin.sh
	tar xf bin.tar.gz
	for f in ./exploit-4*.py; do ./check-attack.sh zookd-exstack $$f; done

.PHONY: check-libc
check-libc: bin.tar.gz shellcode.bin
	./check-bin.sh
	tar xf bin.tar.gz
	for f in ./exploit-5*.py; do ./check-attack.sh zookd-nxstack $$f; done

.PHONY: check-challenge
check-challenge: bin.tar.gz shellcode.bin
	./check-bin.sh
	tar xf bin.tar.gz
	./check-attack.sh zookd-nxstack ./exploit-challenge.py

.PHONY: check-crash-fixed
check-crash-fixed: clean $(PROGS) shellcode.bin
	for f in ./exploit-2*.py; do ./check-crash.sh zookd-exstack $$f; done

.PHONY: check-exstack-fixed
check-exstack-fixed: clean $(PROGS) shellcode.bin
	for f in ./exploit-4*.py; do ./check-attack.sh zookd-exstack $$f; done

.PHONY: check-libc-fixed
check-libc-fixed: clean $(PROGS) shellcode.bin
	for f in ./exploit-5*.py; do ./check-attack.sh zookd-nxstack $$f; done

.PHONY: check-fixed
check-fixed: check-crash-fixed check-exstack-fixed check-libc-fixed

.PHONY: check-zoobar
check-zoobar:
	./check-zoobar.py

.PHONY: check-lab1
check-lab1: check-zoobar check-crash check-exstack check-libc check-challenge

.PHONY: check-lab2
check-lab2: $(PROGS)
	./check-lab2.py

.PHONY: check-lab3
check-lab3:
	./check-lab3.py

.PHONY: check-lab4
check-lab4: $(PROGS)
	./check-lab4.sh

.PHONY: clean
clean:
	if [ -x zookclean.py ]; then ./zookclean.py; fi
	rm -f *.o *.pyc *.bin $(PROGS)

handin.tar.gz: clean
	tar cf - `find . -type f | grep -v '^\.*$$' | grep -v '/\.git/' | grep -v 'handin\.tar\.gz' | grep -v 'zip$$'` | gzip > $@

# Workaround for the VM not having zip installed (will be fixed next year)
zip:
	rm -f $@.tmp
	wget https://web.mit.edu/6.858/2023/zip -O $@.tmp
	chmod 755 $@.tmp
	mv $@.tmp $@

handin.zip: clean zip
	-rm -f $@
	find . -type f | grep -v '^\.*$$' | grep -v '/\.git/' | grep -v 'handin\.tar\.gz' | grep -v 'zip$$' | ./zip -r@ $@

.PHONY: typecheck
typecheck: $(wildcard *.py zoobar/*.py)
	mypy --strict $^


## For staff use only
staff-bin: zookd zookd-exstack zookd-nxstack
	tar cvzf bin.tar.gz $^
.PHONY: staff-bin

export:
	rm -rf export
	python export-lab.py -o export
.PHONY: export

export-check: export
	for D in export/*; do make -C $$D; done
	( cd export/lab1 && ./check-zoobar.py )
.PHONY: export-check
