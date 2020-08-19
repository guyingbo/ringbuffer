class OverflowException(Exception):
    pass


def _chr_len(x: int):
    return len(repr(chr(x))) - 2


# RingBuffer structure
# @: data, -: blank
# [------------------------------------------] initial state
#  ^head&tail
#  ^data
# [@@@@@@@@----------------------------------] after first push
#  ^tail   ^head
# [-----@@@@@@@@@----------------------------] after first pull
#       ^tail    ^head
# [@@@------------------------------@@@@@@@@@] after first push over size
#     ^head                         ^tail
# [------------------------------------------] empty
#                   ^head&tail
# [@@@@@@@@@@@@@@@@-@@@@@@@@@@@@@@@@@@@@@@@@@] full
#                  ht
class RingBuffer:
    def __init__(self, size: int):
        if size < 2:
            raise ValueError("size must > 1")
        self.buf = bytearray(size)
        self.head = 0
        self.tail = 0
        self.size = size

    def __len__(self) -> int:
        return len(self.buf)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({bytes(self.buf)!r}, head={self.head}, tail={self.tail})"

    @property
    def data_size(self) -> int:
        if self.tail < self.head:
            return self.head - self.tail
        elif self.tail == self.head:
            return 0
        else:
            return self.head + self.size - self.tail

    @property
    def available_size(self) -> int:
        return self.size - self.data_size - 1

    @property
    def no_mcp_size(self) -> int:
        if self.tail < self.head:
            return self.head - self.tail
        elif self.tail == self.head:
            return 0
        else:
            return self.size - self.tail

    def clear(self) -> None:
        self.head = self.tail = 0

    def resize(self, size) -> None:
        if size < 2:
            raise ValueError("size must > 1")
        if self.size == size:
            return
        elif self.size < size:
            self.buf.extend(b"\x00" * (size - self.size))
        else:  # self.size > size
            del self.buf[self.size - size :]
        self.size = size
        self.clear()

    def pprint(self) -> None:
        print("\n", repr(self.buf), sep="")
        if self.head < self.tail:
            len0 = len(repr(self.buf[: self.head])) - 2
            len1 = _chr_len(self.buf[self.head])
            len2 = len(repr(self.buf[self.head + 1 : self.tail])) - 14
            len3 = _chr_len(self.buf[self.tail])
            print(f"{' '*len0}{'s'*len1}{' '*len2}{'e'*len3}")
        elif self.head > self.tail:
            len0 = len(repr(self.buf[: self.tail])) - 2
            len1 = _chr_len(self.buf[self.tail])
            len2 = len(repr(self.buf[self.tail + 1 : self.head])) - 14
            len3 = _chr_len(self.buf[self.head])
            print(f"{' '*len0}{'s'*len1}{' '*len2}{'e'*len3}")
        else:  # self.head == self.tail:
            len0 = len(repr(self.buf[: self.tail])) - 2
            len1 = _chr_len(self.buf[self.tail])
            print(f"{' '*len0}{'^'*len1}")

    def is_full(self) -> bool:
        return self.head + 1 == self.tail

    def is_empty(self) -> bool:
        return self.head == self.tail

    def next(self) -> memoryview:
        limit = (self.tail - 1) % self.size
        if self.head < limit:
            return memoryview(self.buf)[self.head : limit]
        elif self.head > limit:
            return memoryview(self.buf)[self.head :]
        else:  # self.head == limit
            raise OverflowException

    def shift(self, nbytes: int) -> None:
        self.head = (self.head + nbytes) % self.size

    def push_bytes(self, data: bytes) -> None:
        length = len(data)
        if length > self.available_size:
            raise OverflowException
        with self.next() as mv:
            if len(mv) >= length:
                mv[:length] = data  # type: ignore
            else:
                shift_len = len(mv)
                mv[:] = data[:shift_len]  # type: ignore
                with memoryview(self.buf)[: self.tail] as mv2:
                    mv2[: length - shift_len] = data[shift_len:]  # type: ignore
        self.shift(length)

    def pull_bytes(self, nbytes: int) -> bytes:
        if nbytes < 1:
            raise ValueError("nbytes must >= 1")
        if self.head < self.tail:
            if self.tail + nbytes <= self.size:
                start = self.tail
                self.tail = (self.tail + nbytes) % self.size
                return bytes(memoryview(self.buf)[start:])
            elif self.head + self.size - self.tail >= nbytes:
                start = self.tail
                self.tail = start + nbytes - self.size
                with memoryview(self.buf) as mv:
                    return b"".join((mv[start:], mv[: self.tail]))
            else:
                raise OverflowException
        elif self.head > self.tail:
            if self.tail + nbytes <= self.head:
                start = self.tail
                self.tail += nbytes
                return bytes(memoryview(self.buf)[start : self.tail])
            else:
                raise OverflowException
        else:  # self.head == self.tail
            raise OverflowException


ring = RingBuffer(16)
ring.pprint()
ring.push_bytes(b"0" * 15)
ring.pprint()
ring.pull_bytes(10)
ring.pprint()
ring.push_bytes(b"1" * 4)
ring.pprint()
ring.resize(32)
ring.pprint()
