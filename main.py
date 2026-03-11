# acmp (Animal Crossing Music Player) - main.py
# Michael D'Argenio
# mjdargen@gmail.com
# https://dargen.io
# https://github.com/mjdargen
import sys
import os
import time
import requests
import datetime
import argparse
import multiprocessing
from dotenv import load_dotenv
# from pydub import AudioSegment
# from pydub.playback import _play_with_simpleaudio
import subprocess

# gets weather based on lat/lon
def get_weather(lat, lon):
    url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}&current=weather_code"
    )

    r = requests.get(url)
    data = r.json()

    code = data["current"]["weather_code"]

    raining_codes = {
        51, 53, 55, 56, 57,
        61, 63, 65, 66, 67,
        80, 81, 82,
        95, 96, 99
    }

    snowing_codes = {
        71, 73, 75,
        77,
        85, 86
    }

    if code in raining_codes:
        return "raining"
    elif code in snowing_codes:
        return "snowing"
    else:
        return "sunny"


# process for handling timeing to switch over
def timing(
    conn, game, lat, lon
):
    prev = None
    while True:
        # get weather
        weather = get_weather(lat, lon)
        # get current time
        now = datetime.datetime.now().strftime("%I%p").lower()
        if now[0] == "0":
            now = now[1:]
        # send message with time and date
        if prev != now:
            if game == "animal-crossing" and weather=="raining":
                conn.send(f"{weather}")
            else:
                conn.send(f"{now}_{weather}")
                
            prev = now

        # compute how long to sleep for
        now = datetime.datetime.now()
        delta = datetime.timedelta(hours=1)
        next_hour = (now + delta).replace(microsecond=0, second=0, minute=0)
        wait_seconds = (next_hour - now).seconds
        time.sleep(wait_seconds)


# process for handling audio
def audio(conn, game, vol):
    DIR_PATH = os.path.dirname(os.path.realpath(__file__))

    # start with silence to initialize objects before loop
    file = os.path.join(DIR_PATH, "silence.mp3")

    playback = subprocess.Popen([
        "ffplay",
        "-nodisp",
        "-autoexit",
        "-loglevel", "quiet",
        file
    ])

    volume = f"volume={vol}"

    while True:
        # check for new message
        if conn.poll():
            name = conn.recv()
            print(f"Switching to {name}.")
            file = os.path.join(DIR_PATH, game, f"{name}.mp3")

            # stop old song
            if playback and playback.poll() is None:
                playback.terminate()

            # play new song
            playback = subprocess.Popen([
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel", "quiet",
                "-af", volume,
                file
            ])

        # song finished, repeat
        if playback.poll() is not None:
            playback = subprocess.Popen([
                "ffplay",
                "-nodisp",
                "-autoexit",
                "-loglevel", "quiet",
                "-af", volume,
                file
            ])

        time.sleep(2)


def main():
    load_dotenv()

    # handle arguments
    games = ["new-horizons", "new-leaf", "wild-world", "animal-crossing"]
    parser = argparse.ArgumentParser(description="Animal Crossing Music Player")
    parser.add_argument("--game", dest="game", required=False, help=f'The valid game options are: {", ".join(games)}.')
    parser.add_argument("--lat", dest="lat", required=True)
    parser.add_argument("--lon", dest="lon", required=True)
    parser.add_argument("--volume", dest="vol", required=False)
    args = parser.parse_args()

    if not args.lat or not args.lon:
        print("lat and lon are required")
        sys.exit(1)

    lat = str(args.lat)
    lon = str(args.lon)

    if not args.game:
        game = "new-horizons"
    elif args.game not in games:
        print("Game not recognized... Choosing New Horizons.")
        game = "new-horizons"
    else:
        game = args.game

    vol_dec = f"{int(args.vol) / 100:.2f}"

    # creating a pipe to communicate between processes
    parent_conn, child_conn = multiprocessing.Pipe()

    # creating processes
    timing_process = multiprocessing.Process(target=timing, args=(child_conn, game, lat, lon))
    audio_process = multiprocessing.Process(target=audio, args=(parent_conn, game, vol_dec))

    # be sure to kill processes if keyboard interrupted
    try:
        # starting timing process
        timing_process.start()
        # starting audio process
        audio_process.start()

        # wait until audio is finished
        audio_process.join()
        # wait until timing is finished
        timing_process.join()
    except KeyboardInterrupt:
        print("Interrupted")
        audio_process.terminate()
        timing_process.terminate()


if __name__ == "__main__":
    main()
