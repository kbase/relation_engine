class Clock:
    def __init__(self):
        self.clocks = ["🕛", "🕐", "🕑", "🕒", "🕓", "🕔", "🕕", "🕖", "🕗", "🕘", "🕙", "🕚"]
        self.clock_pos = -1

    def tick(self):
        self.clock_pos += 1
        if self.clock_pos >= len(self.clocks):
            self.clock_pos = 0
        return self.clocks[self.clock_pos]
