import csv
import json
import cv2
import argparse
import numpy as np
from typing import Dict, List, Tuple, Optional, Set
import os

class AnnotationProcessor:
    def __init__(self, csv_path: str, video_path: str):
        self.csv_path = csv_path
        self.video_path = video_path
        self.fps = self._get_video_fps()
        self.video_duration = self._get_video_duration()
        self.annotations = []
        self.attribute_mappings = {}
        self.annotation_type_mapping = {}
        
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
        
        # Create mapping for annotation type (MP or Error)
        for option_id, option_value in self.attribute_mappings.get('6', {}).get('options', {}).items():
            self.annotation_type_mapping[option_id] = option_value
        
        # Parse annotations
        reader = csv.reader(lines[10:])  # Skip header lines
        annotation_count = 0
        for row in reader:
            if not row:
                continue
            metadata_id, file_list, flags, temporal_coords, spatial_coords, metadata = row
            
            temporal = json.loads(temporal_coords)
            metadata = json.loads(metadata)
            
            # Add annotation type to each annotation
            annotation_type = self.annotation_type_mapping.get(metadata.get('6', '0'), 'MP')
            
            self.annotations.append({
                'start_time': temporal[0],
                'end_time': temporal[1],
                'metadata': metadata,
                'type': annotation_type
            })
            annotation_count += 1
        
        print(f"Parsed {annotation_count} annotations")
        
    def fill_gaps(self):
        print("Filling gaps between annotations...")
        # Process MP and Error annotations separately
        mp_annotations = [ann for ann in self.annotations if ann['type'] == 'MP']
        error_annotations = [ann for ann in self.annotations if ann['type'] == 'Error']
        
        # Process MP annotations
        if mp_annotations:
            # Sort annotations by start time
            mp_annotations.sort(key=lambda x: x['start_time'])
            
            # Extend first annotation to start of video
            if mp_annotations[0]['start_time'] > 0:
                print(f"Extending first MP annotation from {mp_annotations[0]['start_time']} to 0")
                mp_annotations[0]['start_time'] = 0
                
            # Fill gaps between annotations
            gap_count = 0
            for i in range(len(mp_annotations) - 1):
                if mp_annotations[i]['end_time'] < mp_annotations[i + 1]['start_time']:
                    gap_count += 1
                    mp_annotations[i]['end_time'] = mp_annotations[i + 1]['start_time']
            
            print(f"Filled {gap_count} gaps between MP annotations")
        
        # Update the annotations list
        self.annotations = mp_annotations + error_annotations
        
    def get_annotation_for_frame(self, frame_time: float, annotation_type: str = 'MP') -> Optional[dict]:
        for ann in self.annotations:
            if ann['type'] == annotation_type and ann['start_time'] <= frame_time <= ann['end_time']:
                return ann
        return None
    
    def format_mp_field(self, verb: str, instrument: str, peg: str, pole: str) -> str:
        # Extract base pole name without _S or _G suffix
        base_pole = pole.split('_')[0] if pole else ''
        
        if verb in ['Touch', 'Untouch']:
            if pole:
                return f"{verb}({peg}, {base_pole})"
            return f"{verb}({instrument}, {peg})"
        elif verb in ['Release', 'Grasp']:
            return f"{verb}({instrument}, {peg})"
        return "Idle"
    
    def parse_error_types(self, error_str: str) -> List[str]:
        if not error_str:
            return ["NO_ERROR"]
        
        # Handle comma-separated error IDs
        error_ids = error_str.split(',')
        error_types = []
        
        for error_id in error_ids:
            error_type = self.attribute_mappings['5']['options'].get(error_id.strip(), '')
            if error_type:
                error_types.append(error_type)
        
        return error_types if error_types else ["NO_ERROR"]
    
    def generate_frame_annotations(self) -> Tuple[List[Dict], List[Dict]]:
        print("Generating frame-by-frame annotations...")
        mp_frame_annotations = []
        error_frame_annotations = []
        total_frames = int(self.video_duration * self.fps)
        
        print(f"Processing {total_frames} frames...")
        for frame_id in range(total_frames):
            if frame_id % 1000 == 0:  # Progress update every 1000 frames
                print(f"Processing frame {frame_id}/{total_frames} ({(frame_id/total_frames*100):.1f}%)")
            
            frame_time = frame_id / self.fps
            mp_ann = self.get_annotation_for_frame(frame_time, 'MP')
            error_ann = self.get_annotation_for_frame(frame_time, 'Error')
            
            # Process MP annotation
            if mp_ann:
                metadata = mp_ann['metadata']
                
                # Get string values for each attribute
                verb = self.attribute_mappings['4']['options'].get(metadata.get('4', '4'), 'Idle')
                instrument = self.attribute_mappings['3']['options'].get(metadata.get('3', ''), '')
                peg = self.attribute_mappings['1']['options'].get(metadata.get('1', ''), '')
                pole = self.attribute_mappings['2']['options'].get(metadata.get('2', ''), '')
                error_ids = metadata.get('5', '')
                error_types = self.parse_error_types(error_ids)
                failure = self.attribute_mappings['7']['options'].get(metadata.get('7', ''), '')
                
                mp = self.format_mp_field(verb, instrument, peg, pole)
            else:
                # Create default annotation for frames without MP data
                verb = 'Idle'
                instrument = ''
                peg = ''
                pole = ''
                error_types = ['NO_ERROR']
                failure = ''
                mp = 'Idle'
            
            # Always add MP annotation for every frame
            mp_frame_annotations.append({
                'frame_id': frame_id,
                'verb': verb,
                'instrument': instrument,
                'peg': peg,
                'pole': pole,
                'error_type': ';'.join(error_types),
                'failure': failure,
                'mp': mp
            })
            
            # Also add to error annotations if there's an error in MP track
            if mp_ann and error_ids and error_types != ["NO_ERROR"]:
                error_frame_annotations.append({
                    'frame_id': frame_id,
                    'error_type': ';'.join(error_types),
                    'failure': failure,
                    'source': 'MP'
                })
            
            # Process Error annotation
            if error_ann:
                metadata = error_ann['metadata']
                error_ids = metadata.get('5', '')
                error_types = self.parse_error_types(error_ids)
                failure = self.attribute_mappings['7']['options'].get(metadata.get('7', ''), '')
                
                error_frame_annotations.append({
                    'frame_id': frame_id,
                    'error_type': ';'.join(error_types),
                    'failure': failure,
                    'source': 'Error'
                })
            # If no error annotation exists, create a default one
            elif not any(e['frame_id'] == frame_id for e in error_frame_annotations):
                error_frame_annotations.append({
                    'frame_id': frame_id,
                    'error_type': 'NO_ERROR',
                    'failure': '',
                    'source': ''
                })
        
        print(f"Generated MP annotations for {len(mp_frame_annotations)} frames")
        print(f"Generated Error annotations for {len(error_frame_annotations)} frames")
        return mp_frame_annotations, error_frame_annotations
    
    def save_csv(self, frame_annotations: List[Dict], output_path: str, fieldnames: List[str]):
        print(f"Saving frame annotations to CSV: {output_path}")
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(frame_annotations)
        print("CSV file saved successfully")
    
    def get_pole_base_color(self, pole_name: str) -> Tuple[str, str]:
        """Extract base color and type (start/goal) from pole name"""
        if not pole_name or '_' not in pole_name:
            return pole_name, ""
        
        parts = pole_name.split('_')
        base_color = parts[0]
        pole_type = parts[1]
        
        return base_color, pole_type
    
    def get_pole_type_symbol(self, pole_type: str) -> str:
        """Get symbol for pole type"""
        if pole_type == 'S':
            return "(Start)"
        elif pole_type == 'G':
            return "(Goal)"
        return ""
        
    def create_annotated_video(self, frame_annotations: List[Dict], output_path: str, crop_coords: Tuple[int, int, int, int] = None):
        """
        Create annotated video with optional cropping
        
        Args:
            frame_annotations: List of frame annotations
            output_path: Output video path
            crop_coords: Tuple of (top_left_x, top_left_y, bottom_right_x, bottom_right_y) for cropping
        """
        print(f"Creating annotated video: {output_path}")
        cap = cv2.VideoCapture(self.video_path)
        original_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        original_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        # Determine output dimensions based on cropping
        if crop_coords:
            top_left_x, top_left_y, bottom_right_x, bottom_right_y = crop_coords
            output_width = bottom_right_x - top_left_x
            output_height = bottom_right_y - top_left_y
            print(f"Cropping video from ({original_width}x{original_height}) to ({output_width}x{output_height})")
            print(f"Crop coordinates: top-left({top_left_x}, {top_left_y}), bottom-right({bottom_right_x}, {bottom_right_y})")
        else:
            output_width = original_width
            output_height = original_height
            print(f"Using original video dimensions: {output_width}x{output_height}")
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(output_path, fourcc, self.fps, (output_width, output_height))
        
        # Define colors for pegs and poles (BGR format)
        color_map = {
            'Cyan': (255, 255, 0),    # BGR for Cyan
            'Magenta': (255, 0, 255), # BGR for Magenta
            'Yellow': (0, 255, 255),  # BGR for Yellow
            'Red': (0, 0, 255),       # BGR for Red
            'Green': (0, 255, 0),     # BGR for Green
            'Blue': (255, 0, 0)       # BGR for Blue
        }
        
        # Define better text colors
        text_colors = {
            'header': (51, 51, 51),        # Dark gray for headers
            'value': (0, 0, 0),            # Black for values
            'error': (0, 0, 255),          # Red for error labels
            'failure': (0, 0, 128)         # Dark red for failure
        }
        
        thickness = 2
        thin_thickness = 1
        
        # Panel settings
        panel_margin = 10
        panel_padding = 10
        
        # Define fonts and styling - use smaller fonts for cropped videos
        main_font = cv2.FONT_HERSHEY_SIMPLEX
        header_font = cv2.FONT_HERSHEY_DUPLEX
        
        if crop_coords:
            # Smaller fonts for cropped videos
            title_font_scale = 0.6
            header_font_scale = 0.5
            value_font_scale = 0.55
            panel_width = 400  # Smaller panel for cropped videos
            line_height = 25
            header_width = 90
        else:
            # Original fonts for full videos
            title_font_scale = 0.8
            header_font_scale = 0.7
            value_font_scale = 0.75
            panel_width = 500
            line_height = 32
            header_width = 110
        
        total_frames = len(frame_annotations)
        frame_idx = 0
        
        print(f"Processing {total_frames} frames for video creation...")
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_idx % 100 == 0:  # Progress update every 100 frames
                print(f"Processing frame {frame_idx}/{total_frames} ({(frame_idx/total_frames*100):.1f}%)")
            
            # Safety check to ensure we don't go out of bounds
            if frame_idx >= len(frame_annotations):
                print(f"Warning: Video has more frames ({frame_idx + 1}) than annotations ({len(frame_annotations)}). Stopping video creation.")
                break
            
            ann = frame_annotations[frame_idx]
            
            # Apply cropping first if specified
            if crop_coords:
                top_left_x, top_left_y, bottom_right_x, bottom_right_y = crop_coords
                frame = frame[top_left_y:bottom_right_y, top_left_x:bottom_right_x]
            
            # Calculate panel height based on content
            panel_height = 200 if crop_coords else 260  # Smaller base height for cropped videos
            
            # Add height for errors if present
            if 'error_type' in ann and ann['error_type'] != 'NO_ERROR':
                error_types = ann['error_type'].split(';')
                panel_height += len(error_types) * line_height
            
            # Add height for failure if present
            if 'failure' in ann and ann['failure']:
                panel_height += line_height
            
            # Create semi-transparent overlay panel
            overlay = frame.copy()
            cv2.rectangle(overlay, 
                         (panel_margin, panel_margin), 
                         (panel_margin + panel_width, panel_margin + panel_height), 
                         (240, 240, 240), -1)  # Light gray background
            
            # Apply transparency
            alpha = 0.85
            cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, frame)
            
            # Add panel border
            cv2.rectangle(frame, 
                         (panel_margin, panel_margin), 
                         (panel_margin + panel_width, panel_margin + panel_height), 
                         (100, 100, 100), 1)  # Gray border
            
            # Add title
            cv2.putText(frame, "Annotation Data", 
                       (panel_margin + panel_padding, panel_margin + panel_padding + 20), 
                       header_font, title_font_scale, 
                       text_colors['header'], thickness)
            
            # Current Y position for text
            y_pos = panel_margin + panel_padding + 60
            
            # Verb
            cv2.putText(frame, "Verb:", 
                      (panel_margin + panel_padding, y_pos), 
                      main_font, header_font_scale, 
                      text_colors['header'], thin_thickness)
            cv2.putText(frame, ann['verb'], 
                      (panel_margin + panel_padding + header_width, y_pos), 
                      main_font, value_font_scale, 
                      text_colors['value'], thickness)
            y_pos += line_height
            
            # Instrument
            cv2.putText(frame, "Instrument:", 
                      (panel_margin + panel_padding, y_pos), 
                      main_font, header_font_scale, 
                      text_colors['header'], thin_thickness)
            cv2.putText(frame, ann['instrument'], 
                      (panel_margin + panel_padding + header_width, y_pos), 
                      main_font, value_font_scale, 
                      text_colors['value'], thickness)
            y_pos += line_height
            
            # Peg
            cv2.putText(frame, "Peg:", 
                      (panel_margin + panel_padding, y_pos), 
                      main_font, header_font_scale, 
                      text_colors['header'], thin_thickness)
            if ann['peg']:
                peg_color = color_map.get(ann['peg'], text_colors['value'])
                cv2.putText(frame, ann['peg'], 
                          (panel_margin + panel_padding + header_width, y_pos), 
                          main_font, value_font_scale, 
                          peg_color, thickness)
            y_pos += line_height
            
            # Pole
            cv2.putText(frame, "Pole:", 
                      (panel_margin + panel_padding, y_pos), 
                      main_font, header_font_scale, 
                      text_colors['header'], thin_thickness)
            if ann['pole']:
                # Extract base color and type
                base_color, pole_type = self.get_pole_base_color(ann['pole'])
                pole_color = color_map.get(base_color, text_colors['value'])
                
                # Show pole base color
                cv2.putText(frame, base_color, 
                          (panel_margin + panel_padding + header_width, y_pos), 
                          main_font, value_font_scale, 
                          pole_color, thickness)
                
                # Show pole type text if applicable
                if pole_type:
                    type_text = self.get_pole_type_symbol(pole_type)
                    symbol_pos = panel_margin + panel_padding + header_width + len(base_color) * 15
                    cv2.putText(frame, type_text, 
                              (symbol_pos, y_pos), 
                              main_font, value_font_scale, 
                              pole_color, thickness)
            y_pos += line_height
            
            # MP
            cv2.putText(frame, "MP:", 
                      (panel_margin + panel_padding, y_pos), 
                      main_font, header_font_scale, 
                      text_colors['header'], thin_thickness)
            cv2.putText(frame, ann['mp'], 
                      (panel_margin + panel_padding + header_width, y_pos), 
                      main_font, value_font_scale, 
                      text_colors['value'], thickness)
            y_pos += line_height
            
            # Error Type - display as list
            if 'error_type' in ann and ann['error_type'] != 'NO_ERROR':
                error_types = ann['error_type'].split(';')
                
                # Error header
                cv2.putText(frame, "Error Types:", 
                          (panel_margin + panel_padding, y_pos), 
                          main_font, header_font_scale, 
                          text_colors['error'], thin_thickness)
                y_pos += line_height
                
                # List each error on a separate line
                for error in error_types:
                    cv2.putText(frame, f"• {error}", 
                              (panel_margin + panel_padding + 20, y_pos), 
                              main_font, value_font_scale, 
                              text_colors['error'], thickness)
                    y_pos += line_height
            
            # Failure
            if 'failure' in ann and ann['failure']:
                cv2.putText(frame, "Failure:", 
                          (panel_margin + panel_padding, y_pos), 
                          main_font, header_font_scale, 
                          text_colors['failure'], thin_thickness)
                cv2.putText(frame, ann['failure'], 
                          (panel_margin + panel_padding + header_width, y_pos), 
                          main_font, value_font_scale, 
                          text_colors['failure'], thickness)
            
            out.write(frame)
            frame_idx += 1
            
        cap.release()
        out.release()
        print("Video creation completed successfully")
    
    def generate_segment_annotations(self) -> List[Dict]:
        """Generate segment-based annotations instead of frame-by-frame"""
        print("Generating segment-based annotations for MP track...")
        
        # First get the raw annotations
        segment_annotations = []
        
        # Process MP annotations
        mp_annotations = [ann for ann in self.annotations if ann['type'] == 'MP']
        
        for ann in mp_annotations:
            metadata = ann['metadata']
            
            # Get string values for each attribute
            verb = self.attribute_mappings['4']['options'].get(metadata.get('4', '4'), 'Idle')
            instrument = self.attribute_mappings['3']['options'].get(metadata.get('3', ''), '')
            peg = self.attribute_mappings['1']['options'].get(metadata.get('1', ''), '')
            pole = self.attribute_mappings['2']['options'].get(metadata.get('2', ''), '')
            error_ids = metadata.get('5', '')
            error_types = self.parse_error_types(error_ids)
            failure = self.attribute_mappings['7']['options'].get(metadata.get('7', ''), '')
            
            mp = self.format_mp_field(verb, instrument, peg, pole)
            
            # Convert time to frame numbers
            start_frame = int(ann['start_time'] * self.fps)
            end_frame = int(ann['end_time'] * self.fps)
            
            segment_annotations.append({
                'start_frame': start_frame,
                'end_frame': end_frame,
                'verb': verb,
                'instrument': instrument,
                'peg': peg,
                'pole': pole,
                'error_type': ';'.join(error_types),
                'failure': failure,
                'mp': mp
            })
        
        print(f"Generated {len(segment_annotations)} MP segment annotations")
        return segment_annotations
    
    def generate_error_segments(self) -> List[Dict]:
        """Generate segment-based annotations for Error track"""
        print("Generating segment-based annotations for Error track...")
        
        # Get error annotations
        error_segments = []
        
        # Process Error annotations
        error_annotations = [ann for ann in self.annotations if ann['type'] == 'Error']
        
        for ann in error_annotations:
            metadata = ann['metadata']
            
            # Get error types and failure
            error_ids = metadata.get('5', '')
            error_types = self.parse_error_types(error_ids)
            failure = self.attribute_mappings['7']['options'].get(metadata.get('7', ''), '')
            
            # Skip if no error
            if error_types == ["NO_ERROR"] and not failure:
                continue
                
            # Convert time to frame numbers
            start_frame = int(ann['start_time'] * self.fps)
            end_frame = int(ann['end_time'] * self.fps)
            
            error_segments.append({
                'start_frame': start_frame,
                'end_frame': end_frame,
                'error_type': ';'.join(error_types),
                'failure': failure,
                'duration_frames': end_frame - start_frame,
                'duration_seconds': ann['end_time'] - ann['start_time']
            })
        
        print(f"Generated {len(error_segments)} Error segment annotations")
        return error_segments
    
    def save_segment_csv(self, segment_annotations: List[Dict], output_path: str, fieldnames: List[str]):
        """Save segment-based annotations to CSV"""
        print(f"Saving segment annotations to CSV: {output_path}")
        with open(output_path, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(segment_annotations)
        print("Segment CSV file saved successfully")

def main():
    parser = argparse.ArgumentParser(description='Process video annotations')
    parser.add_argument('csv_path', help='Path to the annotation CSV file')
    parser.add_argument('video_path', help='Path to the video file')
    parser.add_argument('output_dir', help='Directory to save output files')
    parser.add_argument('--mp_output', help='Filename for MP annotations CSV (default: mp_annotations.csv)', default='mp_annotations.csv')
    parser.add_argument('--error_output', help='Filename for Error annotations CSV (default: error_annotations.csv)', default='error_annotations.csv')
    parser.add_argument('--segment_output', help='Filename for segment-based annotations CSV (default: segment_annotations.csv)', default='segment_annotations.csv')
    parser.add_argument('--error_segment_output', help='Filename for error segment annotations CSV (default: error_segments.csv)', default='error_segments.csv')
    parser.add_argument('--video_output', help='Filename for annotated video (default: annotated_video.mp4)', default='annotated_video.mp4')
    parser.add_argument('--generate_video', help='Generate annotated video (default: False)', action='store_true', default=False)
    parser.add_argument('--crop_top_left_x', type=int, help='Top-left X coordinate for cropping (default: 73)', default=73)
    parser.add_argument('--crop_top_left_y', type=int, help='Top-left Y coordinate for cropping (default: 65)', default=65)
    parser.add_argument('--crop_bottom_right_x', type=int, help='Bottom-right X coordinate for cropping (default: 1832)', default=1832)
    parser.add_argument('--crop_bottom_right_y', type=int, help='Bottom-right Y coordinate for cropping (default: 960)', default=960)
    parser.add_argument('--no_crop', help='Disable cropping and use original video dimensions', action='store_true', default=False)
    
    args = parser.parse_args()
    
    # Create output directory if it doesn't exist
    os.makedirs(args.output_dir, exist_ok=True)
    
    # Define output paths
    mp_csv_path = os.path.join(args.output_dir, args.mp_output)
    error_csv_path = os.path.join(args.output_dir, args.error_output)
    segment_csv_path = os.path.join(args.output_dir, args.segment_output)
    error_segment_path = os.path.join(args.output_dir, args.error_segment_output)
    video_path = os.path.join(args.output_dir, args.video_output)
    
    print(f"\nStarting annotation processing...")
    print(f"Input CSV: {args.csv_path}")
    print(f"Input Video: {args.video_path}")
    print(f"Output Directory: {args.output_dir}")
    print(f"MP Annotations CSV: {mp_csv_path}")
    print(f"Error Annotations CSV: {error_csv_path}")
    print(f"MP Segment Annotations CSV: {segment_csv_path}")
    print(f"Error Segment Annotations CSV: {error_segment_path}")
    if args.generate_video:
        print(f"Output Video: {video_path}")
        if args.no_crop:
            print("Cropping: Disabled (using original dimensions)")
        else:
            print(f"Cropping: Enabled - top-left({args.crop_top_left_x}, {args.crop_top_left_y}), "
                  f"bottom-right({args.crop_bottom_right_x}, {args.crop_bottom_right_y})")
    else:
        print("Video generation is disabled")
    print()
    
    processor = AnnotationProcessor(args.csv_path, args.video_path)
    processor.parse_csv()
    processor.fill_gaps()
    
    # Generate and save frame-by-frame annotations
    mp_annotations, error_annotations = processor.generate_frame_annotations()
    mp_fieldnames = ['frame_id', 'verb', 'instrument', 'peg', 'pole', 'error_type', 'failure', 'mp']
    processor.save_csv(mp_annotations, mp_csv_path, mp_fieldnames)
    error_fieldnames = ['frame_id', 'error_type', 'failure', 'source']
    processor.save_csv(error_annotations, error_csv_path, error_fieldnames)
    
    # Generate and save MP segment-based annotations
    segment_annotations = processor.generate_segment_annotations()
    mp_segment_fieldnames = ['start_frame', 'end_frame', 'verb', 'instrument', 'peg', 'pole', 'error_type', 'failure', 'mp']
    processor.save_segment_csv(segment_annotations, segment_csv_path, mp_segment_fieldnames)
    
    # Generate and save Error segment-based annotations
    error_segments = processor.generate_error_segments()
    error_segment_fieldnames = ['start_frame', 'end_frame', 'error_type', 'failure', 'duration_frames', 'duration_seconds']
    processor.save_segment_csv(error_segments, error_segment_path, error_segment_fieldnames)
    
    # Create annotated video if enabled
    if args.generate_video:
        print("Generating annotated video...")
        
        # Prepare cropping coordinates
        if args.no_crop:
            crop_coords = None
            print("Cropping disabled - using original video dimensions")
        else:
            crop_coords = (args.crop_top_left_x, args.crop_top_left_y, 
                          args.crop_bottom_right_x, args.crop_bottom_right_y)
            print(f"Using crop coordinates: top-left({args.crop_top_left_x}, {args.crop_top_left_y}), "
                  f"bottom-right({args.crop_bottom_right_x}, {args.crop_bottom_right_y})")
        
        processor.create_annotated_video(mp_annotations, video_path, crop_coords)
    
    print("\nProcessing completed successfully!")

if __name__ == '__main__':
    main()
