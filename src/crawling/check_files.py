from pathlib import Path

def check_files():
    raw_dir = Path(__file__).parent.parent.parent / 'data' / 'raw'
    print(f"Checking directory: {raw_dir}")
    
    # 모든 JSON 파일 검색
    json_files = list(raw_dir.glob('**/*.json'))
    print("\nFound JSON files:")
    for file in json_files:
        print(f"- {file.relative_to(raw_dir)}")
        
    # detailed 디렉토리 검색
    detailed_dirs = list(raw_dir.glob('recipes_detailed_*'))
    print("\nFound detailed directories:")
    for dir in detailed_dirs:
        print(f"- {dir.relative_to(raw_dir)}")
        # 디렉토리 내 파일 검색
        for file in dir.glob('*.json'):
            print(f"  - {file.name}")

if __name__ == "__main__":
    check_files()