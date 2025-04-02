#!/usr/bin/env bash

# sudo apt-get install sox libsox-fmt-all jq curl wget

if [ -z "$3" ]; then
    echo 'Usage: generate_test_wav.sh <OUTPUT_DIR> <LANGUAGE> <TEXT> <HA_TOKEN> [<HA_URL>]'
    exit 1
fi

this_dir="$( cd "$( dirname "$0" )" && pwd )"
base_dir="$(dirname "${this_dir}")"

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
temp_noise_path=$(mktemp --suffix=.wav)
trap 'rm -f "${temp_wav_path}" "${temp_noise_path}"' EXIT

#     compand 0.02,0.05 -60,-60,-30,-10,-20,0 -8 \
#     overdrive 5 \
#     gain -5 \
#     lowpass 1000 highpass 200 \

curl -X POST \
    -H "Authorization: Bearer ${ha_token}" \
    -H 'Content-Type: application/json' \
    -d "{ \"engine_id\": \"tts.home_assistant_cloud\", \"message\": \"${tts_text}\", \"language\": \"${tts_lang}\" }" \
    "${ha_url}/api/tts_get_url" \
    | jq .url \
    | xargs wget -O - \
    | sox -t mp3 - -r 16000 -c 1 -e signed-integer -b 16 -t wav "${temp_wav_path}" \
    lowpass 2000 highpass 200 \
    reverb 50 50 100 \
    pad 0.2

sox "${base_dir}/tests/wav/background_noise.wav" "${temp_noise_path}" \
    vol 3 \
    trim 0 "$(soxi -D "${temp_wav_path}")"

sox -m "${temp_wav_path}" \
    "${temp_noise_path}" \
    "${temp_wav_path}" \
    -b 16 \
    "${wav_path}"

echo "${wav_path}"
