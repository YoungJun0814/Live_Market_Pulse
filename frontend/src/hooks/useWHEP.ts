import { useEffect, useRef, useState } from "react";

interface UseWHEPResult {
  stream: MediaStream | null;
  error: Error | null;
  isConnected: boolean;
}

async function waitForIceGathering(pc: RTCPeerConnection) {
  if (pc.iceGatheringState === "complete") {
    return;
  }

  await new Promise<void>((resolve) => {
    const onIceGatheringStateChange = () => {
      if (pc.iceGatheringState === "complete") {
        pc.removeEventListener("icegatheringstatechange", onIceGatheringStateChange);
        resolve();
      }
    };

    pc.addEventListener("icegatheringstatechange", onIceGatheringStateChange);
  });
}

export function useWHEP(endpointUrl?: string): UseWHEPResult {
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [error, setError] = useState<Error | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const pcRef = useRef<RTCPeerConnection | null>(null);

  useEffect(() => {
    if (!endpointUrl) {
      setStream(null);
      setError(null);
      setIsConnected(false);
      return;
    }

    let isMounted = true;
    let resourceUrl: string | null = null;
    const abortController = new AbortController();
    const pc = new RTCPeerConnection();
    pcRef.current = pc;

    pc.addTransceiver("video", { direction: "recvonly" });
    pc.addTransceiver("audio", { direction: "recvonly" });

    pc.ontrack = (event) => {
      if (!isMounted || !event.streams[0]) {
        return;
      }
      setStream(event.streams[0]);
      setIsConnected(true);
      setError(null);
    };

    pc.onconnectionstatechange = () => {
      if (!isMounted) {
        return;
      }
      if (pc.connectionState === "failed" || pc.connectionState === "closed") {
        setError(new Error(`WebRTC connection ${pc.connectionState}`));
        setIsConnected(false);
      }
    };

    const negotiate = async () => {
      try {
        const offer = await pc.createOffer();
        await pc.setLocalDescription(offer);
        await waitForIceGathering(pc);

        const response = await fetch(endpointUrl, {
          method: "POST",
          headers: {
            "Content-Type": "application/sdp",
          },
          body: pc.localDescription?.sdp ?? offer.sdp ?? "",
          signal: abortController.signal,
        });

        if (!response.ok) {
          throw new Error(`WHEP endpoint returned ${response.status}`);
        }

        resourceUrl = response.headers.get("location");
        const answerSdp = await response.text();
        await pc.setRemoteDescription({
          type: "answer",
          sdp: answerSdp,
        });
      } catch (caughtError) {
        if (!isMounted) {
          return;
        }
        setError(
          caughtError instanceof Error
            ? caughtError
            : new Error("WHEP negotiation failed"),
        );
      }
    };

    void negotiate();

    return () => {
      isMounted = false;
      abortController.abort();
      setIsConnected(false);
      pc.close();
      if (resourceUrl) {
        void fetch(resourceUrl, { method: "DELETE" }).catch(() => undefined);
      }
    };
  }, [endpointUrl]);

  return { stream, error, isConnected };
}
