import React, { useState, useEffect } from "react";
import io, { Socket } from "socket.io-client";
import RecordRTC, { StereoAudioRecorder } from "recordrtc";
import {
  ChakraProvider,
  Box,
  Button,
  VStack,
  Text,
  HStack,
  Flex,
  useToast,
  Icon,
  keyframes,
} from "@chakra-ui/react";
import { FaMicrophone } from "react-icons/fa";
import "./App.css";

interface TranscriptionResult {
  text: string;
  timestamp: string;
  speakerId?: string; // Updated to handle speaker IDs from the backend
}

const App: React.FC = () => {
  const [recorder, setRecorder] = useState<RecordRTC | null>(null);
  const [socket, setSocket] = useState<Socket | null>(null);
  const [transcriptions, setTranscriptions] = useState<TranscriptionResult[]>([]);
  const [currentTranscription, setCurrentTranscription] = useState<string>(""); // Current sentence being transcribed
  const [chapterTitles, setChapterTitles] = useState<string[]>([]); // State for chapter titles
  const [checkboxFlags, setCheckboxFlags] = useState({
    SymptomOrSign: false,
    Diagnosis: false,
    BodyStructure: false,
    Time: false,
    TreatmentName: false,
  });
  
  const [isListening, setIsListening] = useState(false);
  const [room, setRoom] = useState<string | null>(null);
  const toast = useToast();

  useEffect(() => {
    // const newSocket = io("https://speech-sdk.azurewebsites.net");
    const newSocket = io("http://localhost:8000");
    setSocket(newSocket);
  
    // Handle partial transcription (replace previous partial transcription)
    newSocket.on("transcription_result", (data: { text: string, speakerId?: string }) => {
      console.log("Partial transcription:", data.text, "Speaker ID:", data.speakerId);
      setCurrentTranscription(`${data.speakerId ? `[Speaker ${data.speakerId}]: ` : "[Diarizing...]"}${data.text}`);
    });
  
    // Handle final transcription results
    newSocket.on("transcription_final_result", (data: { text: string, speakerId?: string }) => {
      console.log("Final transcription:", data.text, "Speaker ID:", data.speakerId);
      const currentTime = new Date().toLocaleTimeString("en-SG", {
        hour: "2-digit",
        minute: "2-digit",
        hour12: true,
        timeZone: "Asia/Singapore",
      });
  
      // Append final transcription to the list
      setTranscriptions((prev) => [
        ...prev,
        {
          text: `${data.speakerId ? `[Speaker ${data.speakerId}: ${currentTime}] ` : `[Speaker Unknown: ${currentTime}] `}${data.text}`,
          timestamp: currentTime,
        },
      ]);
  
      setCurrentTranscription(""); // Clear the current transcription after finalization
    });

    // Handle receiving chapter titles from the backend
    newSocket.on("chapter_titles", (data: { titles: string }) => {
      setChapterTitles(data.titles.split('\n')); // Split the titles into an array
    });

    // Handle checkbox flags from the backend
    newSocket.on("checkbox_flags", (data) => {
      setCheckboxFlags(data.flags); // Update the checkbox flags state with incoming data
    });
    
  
    // Join the room when connected
    newSocket.on("join_room", (data: { room: string }) => {
      setRoom(data.room);
    });
  
    return () => {
      newSocket.close();
    };
  }, []);  


  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      const newRecorder = new RecordRTC(stream, {
        type: "audio",
        mimeType: "audio/wav",
        recorderType: StereoAudioRecorder,
        numberOfAudioChannels: 1,
        desiredSampRate: 16000, // 16kHz as per Azure config
        timeSlice: 250, // reduced timeSlice to 250ms
        ondataavailable: (blob: Blob) => {
          if (socket && socket.connected) {
            const reader = new FileReader();
            reader.onloadend = () => {
              const arrayBuffer = reader.result as ArrayBuffer;
              socket.emit("audio_data", arrayBuffer);
            };
            reader.readAsArrayBuffer(blob);
          }
        },
      });

      newRecorder.startRecording();
      setRecorder(newRecorder);

      await fetch("http://0.0.0.0:8000/start_transcription", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ room }),
      });

      setIsListening(true);

      toast({
        title: "Recording started",
        status: "success",
        duration: 2000,
        isClosable: true,
      });
    } catch (error) {
      console.error("Error starting recording:", error);
      toast({
        title: "Error starting recording",
        status: "error",
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const stopRecording = async () => {
    try {
      setIsListening(false);
      if (recorder) {
        recorder.stopRecording(() => {
          console.log("Recording stopped.");
        });
        setRecorder(null);

        await fetch("http://0.0.0.0:8000/stop_transcription", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ room }),
        });

        toast({
          title: "Recording stopped",
          status: "info",
          duration: 2000,
          isClosable: true,
        });
      }
    } catch (error) {
      console.error("Error stopping recording:", error);
      toast({
        title: "Error stopping recording",
        status: "error",
        duration: 2000,
        isClosable: true,
      });
    }
  };

  const waveAnimation = keyframes`
    0% { transform: scaleY(1); }
    50% { transform: scaleY(0.5); }
    100% { transform: scaleY(1); }
  `;

  // Layout for the right-hand side chapter titles
  const renderChapterTitles = () => {
    return (
      <VStack align="flex-start" spacing={2} p={4} boxShadow="md" bg="gray.50" borderRadius="md" w="100%">
        <Text fontWeight="bold">Chapter Titles</Text>
        {chapterTitles.map((title, index) => (
          <Text key={index} fontSize="sm">
            {title}
          </Text>
        ))}
      </VStack>
    );
  };

  const renderCheckboxFlags = () => {

    // Map of display texts for each checkbox key
    const checkboxTextMap: { [key: string]: string } = {
      SymptomOrSign: "[SymptomOrSign] Did you obtain information about the symptoms the patient is facing?",
      Diagnosis: "[Diagnosis] Have you diagnosed the patient's condition?",
      BodyStructure: "[BodyStructure] Did you discuss which part of the body the ailment is occurring at?",
      Time: "[Time] Did you obtain information about the duration of the patient's condition and/or the onset of the patient's condition?",
      TreatmentName: "[TreatmentName] Have you offered steps or advice on how the patient should proceed with the treatment?"
    };

    return (
      <VStack align="flex-start" spacing={5} p={4} boxShadow="md" bg="gray.50" borderRadius="md" w="100%">
        <Text fontWeight="bold">Entity Flags</Text>
        {Object.entries(checkboxFlags).map(([key, value]) => (
          <HStack key={key} spacing={3}>
            <input type="checkbox" checked={value} readOnly />
            <Text fontSize="sm">{checkboxTextMap[key] || key}</Text> {/* Display custom text or fallback to key */}
          </HStack>
        ))}
      </VStack>
    );
  };
  

  return (
    <ChakraProvider>
      <Flex direction="row" p={4} w="100%" maxW="1600px">
        
        {/* Transcription Section */}
        <Box flex="1" p={4}>
          <VStack spacing={4}>
            <HStack spacing={4}>
              <Button colorScheme="blue" onClick={startRecording} disabled={isListening}>
                Start Recording
              </Button>
              <Button colorScheme="red" onClick={stopRecording} disabled={!isListening}>
                Stop Recording
              </Button>
            </HStack>
            {isListening && (
              <Flex direction="column" alignItems="center">
                <Icon as={FaMicrophone} w={12} h={12} color="#E54809" css={{ animation: `${waveAnimation} 2s infinite` }} />
                <Text fontSize="xl" fontWeight="bold">
                  Listening...
                </Text>
              </Flex>
            )}
            <Box w="100%" maxW="800px" pt={4} boxShadow="md" bg="gray.200">
              <VStack spacing={2} align="stretch">
                {transcriptions.map((item, index) => (
                  <Flex key={index} direction="column" alignItems="flex-start" margin={2}>
                    <Box p={3} borderRadius="md" maxW="100%" bg="white">
                      <Text>{item.text}</Text>
                    </Box>
                  </Flex>
                ))}
                {currentTranscription && (
                  <Flex direction="column" alignItems="flex-start" margin={2}>
                    <Box p={3} borderRadius="md" maxW="100%" bg="yellow.100">
                      <Text>{currentTranscription}</Text>
                    </Box>
                  </Flex>
                )}
              </VStack>
            </Box>
          </VStack>
        </Box>

        {/* Chapter Titles Section */}
        <Box flex="0.5" p={4}>
          {renderChapterTitles()}
        </Box>

        {/* Checkbox Flags Section */}
        <Box flex="0.4" p={4}>
          {renderCheckboxFlags()}
        </Box>
      </Flex>
    </ChakraProvider>
  );
};

export default App;
