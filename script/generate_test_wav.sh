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
curl -X POST \
    -H "Authorization: Bearer ${ha_token}" \
    -H 'Content-Type: application/json' \
    -d "{ \"engine_id\": \"tts.home_assistant_cloud\", \"message\": \"${tts_text}\", \"language\": \"${tts_lang}\" }" \
    "${ha_url}/api/tts_get_url" \
    | jq .url \
    | xargs wget -O - \
    | sox -t mp3 - -r 16000 -c 1 -e signed-integer "${wav_path}" \
    lowpass 3000 highpass 200 \
    compand 0.02,0.05 -60,-60,-30,-10,-20,0 -8 \
    overdrive 5 \
    gain -8 \
    reverb 30 30 100

echo "${wav_path}"
