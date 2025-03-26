import csv
import json
import cv2
import argparse
import numpy as np
from typing import Dict, List, Tuple, Optional

class AnnotationProcessor:
    def __init__(self, csv_path: str, video_path: str):
        self.csv_path = csv_path
        self.video_path = video_path
        self.fps = self._get_video_fps()
        self.video_duration = self._get_video_duration()
        self.annotations = []
        self.attribute_mappings = {}
        
    def _get_video_fps(self) -> float:
        cap = cv2.VideoCapture(self.video_path)
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return fps
    
    def _get_video_duration(self) -> float:
        cap = cv2.VideoCapture(self.video_path)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        cap.release()
        return frame_count / fps
    
    def parse_csv(self):
        print("Parsing CSV file...")
        with open(self.csv_path, 'r') as f:
            lines = f.readlines()
            
        # Parse attribute definitions
        attribute_line = next(line for line in lines if line.startswith('# ATTRIBUTE ='))
        self.attribute_mappings = json.loads(attribute_line.replace('# ATTRIBUTE = ', ''))
        print("Parsed attribute mappings")
        
        # Parse annotations
        reader = csv.reader(lines[10:])  # Skip header lines
        annotation_count = 0
        for row in reader:
            if not row:
                continue
            metadata_id, file_list, flags, temporal_coords, spatial_coords, metadata = row
            
            temporal = json.loads(temporal_coords)
            metadata = json.loads(metadata)
            
            self.annotations.append({
                'start_time': temporal[0],
                'end_time': temporal[1],
                'metadata': metadata
            })
            annotation_count += 1
        
        print(f"Parsed {annotation_count} annotations")
        
    def fill_gaps(self):
        print("Filling gaps between annotations...")
        # Sort annotations by start time
        self.annotations.sort(key=lambda x: x['start_time'])
        
        # Extend first annotation to start of video
        if self.annotations[0]['start_time'] > 0:
            print(f"Extending first annotation from {self.annotations[0]['start_time']} to 0")
            self.annotations[0]['start_time'] = 0
            
        # Fill gaps between annotations
        gap_count = 0
        for i in range(len(self.annotations) - 1):
            if self.annotations[i]['end_time'] < self.annotations[i + 1]['start_time']:
                gap_count += 1
                self.annotations[i]['end_time'] = self.annotations[i + 1]['start_time']
                
        # Extend last annotation to end of video
        if self.annotations[-1]['end_time'] < self.video_duration:
            print(f"Extending last annotation from {self.annotations[-1]['end_time']} to {self.video_duration}")
            self.annotations[-1]['end_time'] = self.video_duration
        
        print(f"Filled {gap_count} gaps between annotations")
        
    def get_annotation_for_frame(self, frame_time: float) -> Optional[dict]:
        for ann in self.annotations:
            if ann['start_time'] <= frame_time <= ann['end_time']:
                return ann
        return None
    
    def format_mp_field(self, verb: str, instrument: str, peg: str, pole: str) -> str:
        if verb in ['Touch', 'Untouch']:
            if pole:
                return f"{verb}({peg}, {pole})"
            return f"{verb}({instrument}, {peg})"
        elif verb in ['Release', 'Grasp']:
            return f"{verb}({instrument}, {peg})"
        return "Idle"
    
    def generate_frame_annotations(self) -> List[Dict]:
        print("Generating frame-by-frame annotations...")
        frame_annotations = []
        total_frames = int(self.video_duration * self.fps)
        
        print(f"Processing {total_frames} frames...")
        for frame_id in range(total_frames):
            if frame_id % 1000 == 0:  # Progress update every 1000 frames
                print(f"Processing frame {frame_id}/{total_frames} ({(frame_id/total_frames*100):.1f}%)")
            
            frame_time = frame_id / self.fps
            ann = self.get_annotation_for_frame(frame_time)
            
            if ann:
                metadata = ann['metadata']
                
                # Get string values for each attribute
                verb = self.attribute_mappings['4']['options'].get(metadata.get('4', '4'), 'Idle')
                instrument = self.attribute_mappings['3']['options'].get(metadata.get('3', ''), '')
                peg = self.attribute_mappings['1']['options'].get(metadata.get('1', ''), '')
                pole = self.attribute_mappings['2']['options'].get(metadata.get('2', ''), '')
                error = self.attribute_mappings['5']['options'].get(metadata.get('5', ''), '')
                
                mp = self.format_mp_field(verb, instrument, peg, pole)
                
                frame_annotations.append({
                    'frame_id': frame_id,
                    'verb': verb,
                    'instrument': instrument,
                    'peg': peg,
                    'pole': pole,
                    'error': error,
                    'mp': mp
                })
        
        print(f"Generated annotations for {len(frame_annotations)} frames")
        return frame_annotations
    
    def save_csv(self, frame_annotations: List[Dict], output_path: str):
        print(f"Saving frame annotations to CSV: {output_path}")
        fieldnames = ['frame_id', 'verb', 'instrument', 'peg', 'pole', 'error', 'mp']
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(frame_annotations)
        print("CSV file saved successfully")
        
    def create_annotated_video(self, frame_annotations: List[Dict], output_path: str):
        print(f"Creating annotated video: {output_path}")
        cap = cv2.VideoCapture(self.video_path)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (width, height))
        
        # Define colors for pegs and poles (BGR format)
        color_map = {
            'Cyan': (255, 255, 0),    # BGR for Cyan
            'Magenta': (255, 0, 255), # BGR for Magenta
            'Yellow': (0, 255, 255),  # BGR for Yellow
            'Red': (0, 0, 255),       # BGR for Red
            'Green': (0, 255, 0),     # BGR for Green
            'Blue': (255, 0, 0)       # BGR for Blue
        }
        
        black = (0, 0, 0)  # BGR for Black
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.7
        thickness = 2
        y_offset = 30
        
        total_frames = len(frame_annotations)
        frame_idx = 0
        
        print(f"Processing {total_frames} frames for video creation...")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % 100 == 0:  # Progress update every 100 frames
                print(f"Processing frame {frame_idx}/{total_frames} ({(frame_idx/total_frames*100):.1f}%)")
            
            ann = frame_annotations[frame_idx]
            
            # Add text annotations
            # Verb (black)
            cv2.putText(frame, f"Verb: {ann['verb']}", (10, y_offset), 
                       font, font_scale, black, thickness)
            
            # Instrument (black)
            cv2.putText(frame, f"Instrument: {ann['instrument']}", (10, y_offset * 2),
                       font, font_scale, black, thickness)
            
            # Peg (label in black, value in corresponding color)
            cv2.putText(frame, "Peg: ", (10, y_offset * 3),
                       font, font_scale, black, thickness)
            if ann['peg']:
                peg_color = color_map.get(ann['peg'], black)
                cv2.putText(frame, ann['peg'], 
                           (10 + int(font_scale * 70), y_offset * 3),
                           font, font_scale, peg_color, thickness)
            
            # Pole (label in black, value in corresponding color)
            cv2.putText(frame, "Pole: ", (10, y_offset * 4),
                       font, font_scale, black, thickness)
            if ann['pole']:
                pole_color = color_map.get(ann['pole'], black)
                cv2.putText(frame, ann['pole'],
                           (10 + int(font_scale * 70), y_offset * 4),
                           font, font_scale, pole_color, thickness)
            
            # Error (black)
            cv2.putText(frame, f"Error: {ann['error']}", (10, y_offset * 5),
                       font, font_scale, black, thickness)
            
            # MP (black)
            cv2.putText(frame, f"MP: {ann['mp']}", (10, y_offset * 6),
                       font, font_scale, black, thickness)
            
            out.write(frame)
            frame_idx += 1
            
        cap.release()
        out.release()
        print("Video creation completed successfully")

def main():
    parser = argparse.ArgumentParser(description='Process video annotations')
    parser.add_argument('csv_path', help='Path to the annotation CSV file')
    parser.add_argument('video_path', help='Path to the video file')
    parser.add_argument('output_csv', help='Path to save the output CSV file')
    parser.add_argument('output_video', help='Path to save the annotated video')
    
    args = parser.parse_args()
    
    print(f"\nStarting annotation processing...")
    print(f"Input CSV: {args.csv_path}")
    print(f"Input Video: {args.video_path}")
    print(f"Output CSV: {args.output_csv}")
    print(f"Output Video: {args.output_video}\n")
    
    processor = AnnotationProcessor(args.csv_path, args.video_path)
    processor.parse_csv()
    processor.fill_gaps()
    frame_annotations = processor.generate_frame_annotations()
    processor.save_csv(frame_annotations, args.output_csv)
    processor.create_annotated_video(frame_annotations, args.output_video)
    
    print("\nProcessing completed successfully!")

if __name__ == '__main__':
    main()
