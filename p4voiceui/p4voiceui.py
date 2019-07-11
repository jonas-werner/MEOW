import boto3
import os
import uuid
import pyaudio
import wave
import RPi.GPIO as GPIO


AWS_ACCESS_KEY_ID       = os.environ["AWS_ACCESS_KEY_ID"]
AWS_SECRET_ACCESS_KEY   = os.environ["AWS_SECRET_ACCESS_KEY"]
AWS_DEFAULT_REGION      = os.environ["AWS_DEFAULT_REGION"]

# FORMAT		= pyaudio.paInt16
# RATE 		= 16000
# CHUNK_SIZE 	= 1024
# MAX_SILENCE = 3
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
RECORD_SECONDS = 3
WAVE_OUTPUT_FILENAME = "voice.wav"

def record_request(WAVE_OUTPUT_FILENAME):

	p = pyaudio.PyAudio()

	stream = p.open(format=FORMAT,
	                channels=CHANNELS,
	                rate=RATE,
	                input=True,
	                frames_per_buffer=CHUNK)

	print("* recording")

	frames = []

	for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
	    data = stream.read(CHUNK)
	    frames.append(data)

	print("* done recording")

	stream.stop_stream()
	stream.close()
	p.terminate()

	wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
	wf.setnchannels(CHANNELS)
	wf.setsampwidth(p.get_sample_size(FORMAT))
	wf.setframerate(RATE)
	wf.writeframes(b''.join(frames))
	wf.close()

	path = os.path.abspath(WAVE_OUTPUT_FILENAME)

	return path

def play_sound(waveFile):
	os.system("mpg321 " + waveFile)


def callLex(path, user):
	recording = open(path, 'rb')
	client = boto3.client('lex-runtime',
							aws_access_key_id=AWS_ACCESS_KEY_ID,
							aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
							region_name=AWS_DEFAULT_REGION)

	r = client.post_content(botName='LightControl', botAlias='$LATEST', userId=user,
	contentType='audio/l16; rate=16000; channels=1',
	# accept='text/plain; charset=utf-8',
	accept="audio/mpeg",
	inputStream=recording)
	print(r)

	audio_stream = r['audioStream'].read()
	r['audioStream'].close()
	f = wave.open("wavefile.wav", 'wb')
	f.setnchannels(2)
	f.setsampwidth(2)
	f.setframerate(16000)
	f.setnframes(0)
	f.writeframesraw(audio_stream)
	f.close()

	return r


def lightControl(lightState):

	if lightState == "on":
		GPIO.output(17,GPIO.HIGH)
	elif lightState == "off":
		GPIO.output(17,GPIO.LOW)
	else:
		print "lightstate unknown: %s" % lightState


def main():

	user = uuid.uuid4().hex

	GPIO.setmode(GPIO.BCM)
	GPIO.setwarnings(False)
	GPIO.setup(17,GPIO.OUT)

	status = ""

	while status != "Fulfilled":
		path = record_request(WAVE_OUTPUT_FILENAME)

		if path is None:
			print('Nothing recorded')
			return

		lexData = callLex(path, user)

		print "############### ORDER STATUS: %s", lexData[u'dialogState']
		status = lexData[u'dialogState']

		if status == "Fulfilled":
			lightState = lexData[u'slots'][u'lightState']
			lightControl(lightState)
		else:
			play_sound("wavefile.wav")


		# clean up temp files
		os.remove("wavefile.wav")
		os.remove(path)



if __name__ == '__main__':
	main()
