#!/usr/bin/env python3

import argparse
import sys
from src.pipeline.generator import PipelineGenerator
from src.pipeline.steps import PipelineStep

def parse_args():
    parser = argparse.ArgumentParser(description='Generate data processing pipeline scripts')
    parser.add_argument('-c', '--config', required=True,
                      help='Path to the configuration YAML file')
    parser.add_argument('-s', '--step', required=True,
                      help='Single pipeline step to generate')
    parser.add_argument('-o', '--output-dir', default='generated_scripts',
                      help='Output directory for generated scripts')
    parser.add_argument('--list-steps', action='store_true',
                      help='List available pipeline steps and exit')
    return parser.parse_args()

def main():
    args = parse_args()
    
    if args.list_steps:
        print("Available pipeline steps:")
        for i, step in enumerate(PipelineStep.get_all_steps(), 1):
            print(f"  {i}. {step}")
        sys.exit(0)
    
    try:
        # Validate single step
        if not PipelineStep.validate_step(args.step):
            raise ValueError(f"Invalid step specified: {args.step}")
        
        generator = PipelineGenerator(args.config)
        generator.write_scripts(args.output_dir, [args.step])
        
        print("\nScript generated successfully!")
        print("To run the pipeline:")
        step_num = PipelineStep.get_step_number(args.step)
        print(f"  ./s{step_num:02d}_{args.step}.sh")
        
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
