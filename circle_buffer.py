class CircleBuffer:
    "a class that creates a circular array"

    def __init__(self, size):
        self.size = size
        self.data = [0] * self.size
        self.current_pointer = 0

    def insert(self,new_data):
        self.data[self.current_pointer] = new_data
        self.calc_next_pointer()

    def calc_next_pointer(self):
        self.current_pointer = ((self.current_pointer + 1) % self.size)


# Test
if __name__ == '__main__':
    test_buffer = CircleBuffer(5)
    test_buffer.insert(0)
    test_buffer.insert(1)
    test_buffer.insert(2)
    test_buffer.insert(3)
    test_buffer.insert(4)
    test_buffer.insert(5)

    expectation = [5,1,2,3,4]
    reality = test_buffer.data
    if expectation == reality:
        print "Test passed"
    else:
        print "Expected %s, got %s" % (expectation, reality)





