#!/bin/bash

echo "Starting Ollama server..."
ollama serve &

#export OMODEL=llama3.3
export OMODEL=llama3.2
echo "Waiting for Ollama server to be active..."
while [ "$(ollama list | grep 'NAME')" == "" ]; do
  sleep 1
done

echo "Ollama server OK"
ollama pull llama3.2
ollama pull llama3.3
ollama pull codellama
ollama pull mistral
ollama pull llama3.2-vision
ollama run $OMODEL