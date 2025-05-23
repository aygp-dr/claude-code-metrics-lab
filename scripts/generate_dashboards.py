#!/usr/bin/env python3
"""
Generate Grafana dashboards from templates using Jinja2
"""
import os
import sys
import argparse
import yaml
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


def load_config(config_file: str, environment: str = None) -> dict:
    """Load configuration from YAML file with optional environment overrides"""
    with open(config_file, 'r') as f:
        config = yaml.safe_load(f)
    
    # Apply environment-specific overrides
    if environment and 'environments' in config and environment in config['environments']:
        env_config = config['environments'][environment]
        config.update(env_config)
        print(f"Applied {environment} environment overrides")
    
    # Handle dashboard UIDs
    if 'DASHBOARD_UIDS' in config:
        for dashboard_type, uid in config['DASHBOARD_UIDS'].items():
            config[f'DASHBOARD_UID_{dashboard_type.upper()}'] = uid
    
    return config


def generate_dashboard(template_file: str, config: dict, output_dir: str) -> str:
    """Generate a dashboard JSON from template and configuration"""
    template_dir = os.path.dirname(template_file)
    template_name = os.path.basename(template_file)
    
    # Setup Jinja2 environment
    env = Environment(
        loader=FileSystemLoader(template_dir),
        trim_blocks=True,
        lstrip_blocks=True
    )
    
    template = env.get_template(template_name)
    
    # Render template with config variables
    rendered = template.render(**config)
    
    # Determine output filename
    dashboard_name = template_name.replace('.template.json', '.json')
    output_file = os.path.join(output_dir, dashboard_name)
    
    # Write rendered dashboard
    os.makedirs(output_dir, exist_ok=True)
    with open(output_file, 'w') as f:
        f.write(rendered)
    
    return output_file


def main():
    parser = argparse.ArgumentParser(description='Generate Grafana dashboards from templates')
    parser.add_argument('--config', '-c', 
                       default='dashboards/templates/config.yaml',
                       help='Configuration file path')
    parser.add_argument('--environment', '-e',
                       choices=['development', 'staging', 'production'],
                       help='Environment-specific configuration')
    parser.add_argument('--template-dir', '-t',
                       default='dashboards/templates',
                       help='Template directory')
    parser.add_argument('--output-dir', '-o',
                       default='dashboards/generated',
                       help='Output directory for generated dashboards')
    parser.add_argument('--templates', nargs='*',
                       help='Specific templates to generate (default: all *.template.json)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Show what would be generated without creating files')
    
    args = parser.parse_args()
    
    # Load configuration
    try:
        config = load_config(args.config, args.environment)
        print(f"Loaded configuration from {args.config}")
    except FileNotFoundError:
        print(f"Error: Configuration file {args.config} not found")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing YAML configuration: {e}")
        sys.exit(1)
    
    # Find template files
    template_dir = Path(args.template_dir)
    if args.templates:
        # Use specified templates
        template_files = [template_dir / f"{t}.template.json" if not t.endswith('.template.json') else template_dir / t 
                         for t in args.templates]
    else:
        # Find all template files
        template_files = list(template_dir.glob('*.template.json'))
    
    if not template_files:
        print(f"No template files found in {template_dir}")
        sys.exit(1)
    
    # Generate dashboards
    generated_files = []
    for template_file in template_files:
        if not template_file.exists():
            print(f"Warning: Template file {template_file} not found, skipping")
            continue
        
        try:
            if args.dry_run:
                print(f"Would generate: {template_file} -> {args.output_dir}")
            else:
                output_file = generate_dashboard(str(template_file), config, args.output_dir)
                generated_files.append(output_file)
                print(f"Generated: {output_file}")
        except Exception as e:
            print(f"Error generating dashboard from {template_file}: {e}")
            sys.exit(1)
    
    if not args.dry_run:
        print(f"\\nSuccessfully generated {len(generated_files)} dashboard(s)")
        if args.environment:
            print(f"Environment: {args.environment}")
        print(f"Output directory: {args.output_dir}")
        
        # Print import instructions
        print("\\nTo import into Grafana:")
        print("1. Open Grafana web interface")
        print("2. Go to Dashboards -> Browse -> Import")
        print("3. Upload the generated JSON files")


if __name__ == "__main__":
    main()