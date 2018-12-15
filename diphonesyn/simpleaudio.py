import pyaudio
import numpy as np
import wave
import math
import random

from time import sleep


#import pylab as pl

# seed the random number generator
random.seed()

# Some default values for the audio format
CHUNK = 256
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 48000
# This is needed for rescaling
MAX_AMP = 2**15 - 1


class Audio(pyaudio.PyAudio):

    def __init__(self, channels=1,
                 rate=RATE,
                 chunk=CHUNK,
                 format=FORMAT):
        # Initialise the parent class
        pyaudio.PyAudio.__init__(self)

        # Set the format to that specified
        self.chan = channels
        self.rate = rate
        self.chunk = chunk
        self.format = format
        self.nptype = self.get_np_type(format)

        # Set the curent data to an empty array of the correct type
        self.data = np.array([], dtype=self.nptype)

        # No streams are open at the moment
        self.istream = None
        self.ostream = None

        # a counter for referencing the data in chunks
        self.chunk_index = 0

    def __del__(self):
        self.terminate()

    # Get a chunk of data from the current input stream
    def get_chunk(self):
        tmpstr = self.istream.read(self.chunk)
        array = np.fromstring(tmpstr, dtype=self.nptype)
        self.data = np.append(self.data, array)
    
    # Put a chunk of data to the current output stream        
    def put_chunk(self):
        slice_from = self.chunk_index*self.chunk
        slice_to = slice_from + self.chunk
        # Slicing a numpy array out of bounds doesn't seem to raise an
        # index error, so we explicitly test and raise the error ourselves
        if slice_to > self.data.shape[0]:
            raise IndexError
        array = self.data[slice_from:slice_to]
        self.ostream.write(array.tostring())
        self.chunk_index += 1
        
    # Open an input stream
    # We just call the inherited open function in the parent class 
    # with the correct format data
    def open_input_stream(self):
        self.istream = self.open(format=self.format,
                                 channels=self.chan,
                                 rate=self.rate,
                                 input=True,
                                 frames_per_buffer=self.chunk)
   
    # Close the input stream
    def close_input_stream(self):
        self.istream.close()
        self.istream = None
      
    # Open an output stream
    def open_output_stream(self):
        self.ostream = self.open(format=self.format,
                                 channels=self.chan,
                                 rate=self.rate,
                                 output=True)
        self.chunk_index = 0
             
    # close the output stream                   
    def close_output_stream(self):
        self.ostream.close()
        self.ostream = None
    
    # Record data
    def record(self, time=5.0):
        # Clear current data
        self.data = np.array([], dtype=self.nptype)
        # Open an inputstream
        self.open_input_stream()
        print("Recording...")
        # Get time*sample_rate values in total, a chunk at a time
        for i in range(0, int(time * self.rate/self.chunk)):
            self.get_chunk()
        print("Done Recording")
        # Close the input stream
        self.close_input_stream()

    # Play the current data
    def play(self):
        # Open an outputstream
        self.open_output_stream()
        # Reset the chunk counter to 0
        self.chunk_index = 0
        print("Playing...")
        # Loop (potentially forever)
        while True:
            # Try to put output a chunk
            try:    
                self.put_chunk()
            # If we run out of data to output, break out of the loop
            except IndexError:
                break
        
        sleep(0.4) # hack to work around a bug in some (non-blocking) audio hardware 
        print("Stopped playing")
        # Close the output stream
        self.close_output_stream()

    # Save the data to a file
    def save(self, path):
        # Create a 'string' of the data
        raw = self.data.tostring()
        # Open the file for writing
        wf = wave.open(path, 'wb')
        # Set the header information
        wf.setnchannels(self.chan)
        wf.setsampwidth(self.get_sample_size(self.format))
        wf.setframerate(self.rate)
        # Write the data
        wf.writeframes(raw)
        # Close the file
        wf.close()
    
    # Load data from a file    
    def load(self, path):
        # Open the file for reading
        wf = wave.open(path, "rb")
        # Get information from the files header
        self.format = self.get_format_from_width(wf.getsampwidth())
        self.nptype = self.get_np_type(self.format)
        self.chan = wf.getnchannels()
        self.rate = wf.getframerate()
        # Set the internal data attribute to an empty array of the right type
        self.data = np.array([], dtype=self.nptype)
        # Read a chunk of data from the file
        raw = wf.readframes(self.chunk)
        # Loop while there is data in the file
        while raw:
            # Convert the raw data to a numpy array
            array = np.fromstring(raw, dtype=self.nptype)
            # Append the array to the class data attribute
            self.data = np.append(self.data, array)
            # Read the next chunk, ready for the next loop iteration
            raw = wf.readframes(self.chunk)
        # Close the file
        wf.close()
    
    # Convert the pyaudio data format type to the numpy type 
    #  - This really needs expanding to deal with other data types, e.g. 8bit and 24bit audio
    def get_np_type(self, type):
        if type == pyaudio.paInt16:
            return np.int16
    
    # Convert the numpy data format type to the pyaudio type    
    def get_pa_type(self, type):
        if type == np.int16:
            return pyaudio.paInt16
    
    # Add an echo the the current audio data
    #   repeat - How many delayed repeats to add
    #   delay  - How long to delay each repeat (in samples)
    def add_echo(self, repeat, delay):
        # get the length of the existing data
        length = self.data.shape[0]
        # create a new array with the required extra length
        array = np.zeros(length + repeat*delay, dtype=np.float)

        # loop for the number of delays + 1
        #  - we use the 0th iteration of the loop to reduce the amplitude of the original
        #    waveform, so when we add to it we don't 'clip'
        for i in range(0, repeat+1):
            # Get start and end times for the current offset
            start = i*delay
            end = length + i*delay
            # Calculate the current scaling factor
            scale = 2**(i+1)
            # Add a scaled version of self.data to 'window' of the new array
            array[start:end] += self.data / scale
        # Set the class data attribute to the new array
        self.data = np.rint(array).astype(self.nptype)

    def rescale(self, val):
        # Check argument passed
        if not 0 <= val <= 1:
            raise ValueError("Expected scaling factor between 0 and 1")

        # find the biggest peak
        # peak = 0
        # length = self.data.shape[0]
        # for i in range(0, length-1):
        #     if abs(self.data[i]) > peak:
        #         peak = abs(self.data[i])

        peak = np.max(np.abs(self.data))

        # Calculate the rescaling factor
        rescale_factor = val*MAX_AMP/peak

        self.data = (self.data * rescale_factor).astype(self.nptype)

    def create_tone(self, frequency, length, amplitude):
        if not 0 <= amplitude <= 1:
            raise ValueError("Expected amplitude between 0 and 1")

        # create new array of requested length
        s = np.zeros(length, self.nptype)

        # iterate through array, creating waveform sample by sample
        for i in range(0, length):
            s[i] = amplitude * MAX_AMP \
                   * math.sin(frequency * i * 2 * math.pi/self.rate)

        # set instance data to the newly created array
        self.data = s

    def create_noise(self, length, amplitude):

        if not 0 <= amplitude <= 1:
            raise ValueError("Expected amplitude between 0 and 1")

        # create new array of requested length
        s = np.zeros(length, self.nptype)

        # iterate through array, creating waveform sample by sample
        for i in range(0, length):
            s[i] = amplitude * MAX_AMP * random.random()

        # set instance data to the newly created array
        self.data = s

    # This version adds to the existing object. 
    # Cons of this approach: changes the original object, 
    #  if used more than once to add more than two objects together 
    #  the relative amplitudes are not maintained due to the scaling
    def add(self, other):
        # Find the length of the longest
        length = max(self.data.shape[0], other.data.shape[0])
        # Create an empty array of this length
        array = np.zeros(length, dtype=self.nptype)
        # Add in each data at half amplitute (so it doesn't clip)
        array += self.data / 2.0
        array += other.data / 2.0
        # Update the stored array in the current object.
        self.data = array

    def __len__(self):
        return self.data.shape[0]

    def get_samplerange(self):
        if self.nptype == np.int16:
            return math.pow(2, 16)

    def compute_fft(self, start, end):
        dur = end - start
        fft = pl.fft(self.data[start:end])
        real_range = np.ceil((dur+1)/2.0)
        fft = fft[0:real_range]
        fft = abs(fft)

        return fft * np.hanning(len(fft))

    def change_speed(self, factor):
        indxs = np.round(np.arange(0, len(self.data), factor))
        indxs = indxs[indxs < len(self.data)].astype(int)
        self.data = self.data[indxs]

    def time_stretch_fft(self, factor, windowsize=1024, overlap=512, apply_hanning=True):
        phase = np.zeros(windowsize)
        if apply_hanning:
            amp_window = np.hanning(windowsize)
        else:
            amp_window = np.ones(windowsize, dtype=np.float)
        result = np.zeros(int(len(self.data) / factor + windowsize))

        for i in np.arange(0, len(self.data)-(windowsize+overlap), overlap*factor, dtype=np.int):
            a1 = self.data[i: i + windowsize]
            a2 = self.data[i + overlap: i + windowsize + overlap]

            s1 = np.fft.fft(amp_window * a1)
            s2 = np.fft.fft(amp_window * a2)
            phase = (phase + np.angle(s2/s1)) % 2*np.pi
            a2_rephased = np.fft.ifft(np.abs(s2)*np.exp(1j*phase))

            i2 = int(i/factor)
            result[i2:i2 + windowsize] += amp_window*np.real(a2_rephased)
        result = ((2**(16-4)) * result/result.max())

        self.data = result.astype(self.nptype)

    def plot_waveform(self, start=0, end=-1, x_unit="samples"):
        array = self.data[start:end]
        num_samples = len(array)
        if x_unit == "samples":
            pl.plot(range(num_samples), array)
            pl.xlabel('Time (Samples)')
        elif x_unit == "time":
            end_time = self.samples_to_time(num_samples)
            y_steps = np.arange(0, end_time, float(end_time) / num_samples)
            pl.plot(y_steps, array)
            pl.xlabel('Time (s)')
        pl.ylabel('Amplitude')
        samplerange = self.get_samplerange()
        pl.ylim([-samplerange/2, samplerange/2])
        pl.show()

    def plot_spectrum(self, array, start=0, end=-1, plot_log=False):
        array = array[start:end]
        len_arr = len(array)
        # print(len_arr)
        freq_axis = np.arange(0, len_arr, 1.0)  # * (self.rate / len_arr)
        if plot_log:
            pl.plot(freq_axis/1000, 10*np.log10(array), color='k')
            pl.ylabel('Power (dB)')
        else:
            pl.plot(freq_axis/1000, array, color='k')
        pl.xlabel('Frequency (kHz)')
        pl.show()


# This version uses a function just defined in the module namespace (i.e. not a method of the class),
# and takes one argument that is a list of audio objects. This allows an arbitrary number of objects and uniform scaling
def sum_audio(audio_objects):
    # Get the length of the longest.
    #   - the max() function when given an iterable object will give the max in that 'list', 
    #   - you can also specifiy a function to use to evaluate the size of each object using key=function_name
    length = len(max(audio_objects, key=len))
    # Work out the required scaling factor to prevent clipping
    scale = 1.0/len(audio_objects)

    # make an array of zeros
    # - should really check that the dtype of each of the objects is the same and use that dtype!
    array = np.zeros(length, dtype=np.int16)
    
    # Add each audio_object to the array
    for obj in audio_objects:
        array += np.rint(obj.data * scale).astype(np.int16)
    
    # Create a new object to return
    new_object = Audio()
    new_object.data = array
    
    return new_object


def test_add():
    c = Audio()
    e = Audio()
    g = Audio()

    c.create_tone(261.63, 240000, 0.8)
    e.create_tone(329.63, 240000, 0.8)
    g.create_tone(392.00, 240000, 0.8)
     
    chord = sum_audio((c, e, g))
        
    chord.play()

if __name__ == "__main__":
    # a = Audio()
    # a.record(3)
    # # a.change_speed(0.5)
    # a.play()
    # a.save("./qqq.wav")

    # b = Audio()
    # b.load("nina48.wav")
    # b.rescale(1.0)
    # # # b.change_speed(0.5)
    # b.play()
    # b.add_echo(4, 10000)
    # # # b.change_speed(0.5)
    # # # b.time_stretch_fft(2.0)
    # # # b.plot_waveform()
    # b.play()
    #
    # test_add()
    #
    # c = Audio()
    # c.create_noise(48000, 0.05)
    # c.play()

    d = Audio()
    d.load('kdt48.wav')
    d.time_stretch_fft(0.9, 4096, 256)
    d.play()