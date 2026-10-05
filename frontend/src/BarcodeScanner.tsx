import { useEffect, useRef, useState } from 'react';

type DetectorResult = { rawValue: string };
type Detector = { detect: (source: HTMLVideoElement) => Promise<DetectorResult[]> };
type DetectorConstructor = new (options: { formats: string[] }) => Detector;

export function BarcodeScanner({ onDetected, onClose }: { onDetected: (value: string) => void; onClose: () => void }) {
 const videoRef = useRef<HTMLVideoElement>(null);
 const [message,setMessage] = useState('Starting camera…');
 const [manual,setManual] = useState('');
 useEffect(() => {
  let stream: MediaStream | undefined; let timer: number | undefined; let active = true;
  const start = async () => {
   const DetectorClass = (window as unknown as { BarcodeDetector?: DetectorConstructor }).BarcodeDetector;
   if (!DetectorClass || !navigator.mediaDevices?.getUserMedia) { setMessage('Camera scanning is not supported here. Type or use a hardware scanner below.'); return; }
   try {
    stream = await navigator.mediaDevices.getUserMedia({ video: { facingMode: { ideal: 'environment' } } });
    if (!videoRef.current || !active) return;
    videoRef.current.srcObject = stream; await videoRef.current.play(); setMessage('Point the camera at a barcode.');
    const detector = new DetectorClass({ formats: ['ean_13','ean_8','code_128','code_39','upc_a','upc_e'] });
    timer = window.setInterval(async () => {
     if (!videoRef.current || videoRef.current.readyState < 2) return;
     const codes = await detector.detect(videoRef.current).catch(() => []);
     if (codes[0]?.rawValue) { onDetected(codes[0].rawValue); }
    }, 400);
   } catch { setMessage('Camera permission was not available. Type or use a hardware scanner below.'); }
  };
  void start();
  return () => { active=false; if(timer) window.clearInterval(timer); stream?.getTracks().forEach(track=>track.stop()); };
 }, [onDetected]);
 return <div className="barcode-scanner" role="dialog" aria-label="Barcode scanner"><video ref={videoRef} muted playsInline/><p>{message}</p><label>Barcode fallback<input autoFocus value={manual} onChange={event=>setManual(event.target.value)} onKeyDown={event=>{if(event.key==='Enter'&&manual.trim()){event.preventDefault();onDetected(manual.trim());}}} placeholder="Type or scan barcode, then press Enter"/></label><div><button type="button" className="button secondary" onClick={onClose}>Close scanner</button><button type="button" className="button primary" disabled={!manual.trim()} onClick={()=>onDetected(manual.trim())}>Use barcode</button></div></div>;
}
