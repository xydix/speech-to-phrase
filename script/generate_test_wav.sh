#!/usr/bin/env bash

# sudo apt-get install sox libsox-fmt-all jq curl wget

if [ -z "$3" ]; then
    echo 'Usage: generate_test_wav.sh <OUTPUT_DIR> <LANGUAGE> <TEXT> <HA_TOKEN> [<HA_URL>]'
    exit 1
fi

output_dir="$1"
tts_lang="$2"
tts_text="$3"
ha_token="$4"
ha_url="$5"

if [ -z "${ha_url}" ]; then
    ha_url='http://localhost:8123'
fi

mkdir -p "${output_dir}"
wav_path="${output_dir}/${tts_text}.wav"

temp_wav_path=$(mktemp --suffix=.wav)
trap 'rm -f "${temp_wav_path}"' EXIT

curl -X POST \
    -H "Authorization: Bearer ${ha_token}" \
    -H 'Content-Type: application/json' \
    -d "{ \"engine_id\": \"tts.home_assistant_cloud\", \"message\": \"${tts_text}\", \"language\": \"${tts_lang}\" }" \
    "${ha_url}/api/tts_get_url" \
    | jq .url \
    | xargs wget -O - \
    | sox -t mp3 - -r 16000 -c 1 -e signed-integer -b 16 -t wav - \
    lowpass 3000 highpass 200 \
    compand 0.02,0.05 -60,-60,-30,-10,-20,0 -8 \
    overdrive 5 \
    gain -8 \
    reverb 40 40 100 | \
    sox - -t wav - pad 0.2 | \
    sox "|sox -r 16000 -c 1 -n -p synth 0.2 sin 1000 vol 0.5" - "${temp_wav_path}"

sox -m "${temp_wav_path}" \
    "|sox -r 16000 -c 1 -n -p synth $(soxi -D "${temp_wav_path}") whitenoise vol 0.01" \
    "|sox -r 16000 -c 1 -n -p synth $(soxi -D "${temp_wav_path}") sin 60-100 vol 0.15" \
    "|sox -r 16000 -c 1 -n -p synth $(soxi -D "${temp_wav_path}") pinknoise vol 0.1 lowpass 3000" \
    -b 16 \
    "${wav_path}"

echo "${wav_path}"
