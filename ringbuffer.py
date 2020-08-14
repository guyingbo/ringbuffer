class OverflowException(Exception):
    pass


def _chr_len(x):
    return len(repr(chr(x))) - 2


# RingBuffer structure
# @: data, -: blank
# [------------------------------------------] initial state
#  ^start&end
#  ^data
# [@@@@@@@@----------------------------------] after first push
#  ^end    ^start
# [-----@@@@@@@@@----------------------------] after first pull
#       ^end     ^start
# [@@@------------------------------@@@@@@@@@] after first push over size
#     ^start                        ^end
# [------------------------------------------] empty
#                   ^start&end
# [@@@@@@@@@@@@@@@@-@@@@@@@@@@@@@@@@@@@@@@@@@] full
#                  se
class RingBuffer:
    def __init__(self, size: int):
        if size < 2:
            raise ValueError("size must > 1")
        self.buf = bytearray(size)
        self.start_pos = 0
        self.end_pos = 0
        self.size = size

    def __len__(self) -> int:
        return len(self.buf)

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({bytes(self.buf)!r}, start={self.start_pos}, end={self.end_pos})"

    @property
    def data_size(self) -> int:
        if self.end_pos < self.start_pos:
            return self.start_pos - self.end_pos
        elif self.end_pos == self.start_pos:
            return 0
        else:
            return self.start_pos + self.size - self.end_pos

    @property
    def available_size(self) -> int:
        return self.size - self.data_size - 1

    @property
    def no_mcp_size(self) -> int:
        if self.end_pos < self.start_pos:
            return self.start_pos - self.end_pos
        elif self.end_pos == self.start_pos:
            return 0
        else:
            return self.size - self.end_pos

    def clear(self) -> None:
        self.start_pos = self.end_pos = 0

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
        if self.start_pos < self.end_pos:
            len0 = len(repr(self.buf[: self.start_pos])) - 2
            len1 = _chr_len(self.buf[self.start_pos])
            len2 = len(repr(self.buf[self.start_pos + 1 : self.end_pos])) - 14
            len3 = _chr_len(self.buf[self.end_pos])
            print(f"{' '*len0}{'s'*len1}{' '*len2}{'e'*len3}")
        elif self.start_pos > self.end_pos:
            len0 = len(repr(self.buf[: self.end_pos])) - 2
            len1 = _chr_len(self.buf[self.end_pos])
            len2 = len(repr(self.buf[self.end_pos + 1 : self.start_pos])) - 14
            len3 = _chr_len(self.buf[self.start_pos])
            print(f"{' '*len0}{'s'*len1}{' '*len2}{'e'*len3}")
        else:  # self.start_pos == self.end_pos:
            len0 = len(repr(self.buf[: self.end_pos])) - 2
            len1 = _chr_len(self.buf[self.end_pos])
            print(f"{' '*len0}{'^'*len1}")

    def is_full(self) -> bool:
        return self.start_pos + 1 == self.end_pos

    def is_empty(self) -> bool:
        return self.start_pos == self.end_pos

    def next(self) -> memoryview:
        limit = (self.end_pos - 1) % self.size
        if self.start_pos < limit:
            return memoryview(self.buf)[self.start_pos : limit]
        elif self.start_pos > limit:
            return memoryview(self.buf)[self.start_pos :]
        else:  # self.start_pos == limit
            raise OverflowException

    def _next2(self) -> memoryview:
        return memoryview(self.buf)[: self.end_pos]

    def shift(self, nbytes: int) -> None:
        self.start_pos = (self.start_pos + nbytes) % self.size

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
                with memoryview(self.buf)[: self.end_pos] as mv2:
                    mv2[: length - shift_len] = data[shift_len:]  # type: ignore
        self.shift(length)

    def pull_bytes(self, nbytes: int) -> bytes:
        if nbytes < 1:
            raise ValueError("nbytes must >= 1")
        if self.start_pos < self.end_pos:
            if self.end_pos + nbytes <= self.size:
                start = self.end_pos
                self.end_pos = (self.end_pos + nbytes) % self.size
                return bytes(memoryview(self.buf)[start:])
            elif self.start_pos + self.size - self.end_pos >= nbytes:
                start = self.end_pos
                self.end_pos = start + nbytes - self.size
                with memoryview(self.buf) as mv:
                    return b"".join((mv[start:], mv[: self.end_pos]))
            else:
                raise OverflowException
        elif self.start_pos > self.end_pos:
            if self.end_pos + nbytes <= self.start_pos:
                start = self.end_pos
                self.end_pos += nbytes
                return bytes(memoryview(self.buf)[start : self.end_pos])
            else:
                raise OverflowException
        else:  # self.start_pos == self.end_pos
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
