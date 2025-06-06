#!/usr/bin/env python3
"""
Pulseway Backend Setup Script
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if required tools are installed"""
    requirements = ['docker', 'docker-compose', 'python3']
    missing = []

    for req in requirements:
        if not shutil.which(req):
            missing.append(req)

    if missing:
        print(f"❌ Missing required tools: {', '.join(missing)}")
        print("Please install these tools before continuing.")
        return False

    print("✅ All required tools are available")
    return True

def create_directories():
    """Create necessary directories"""
    directories = ['../data', '../logs', '../backups']

    for directory in directories:
        Path(directory).mkdir(exist_ok=True)
        print(f"✅ Created directory: {directory.name}")

def setup_environment():
    """Setup environment configuration"""
    env_example = Path('../.env.example')
    env_file = Path('../.env')

    if not env_file.exists():
        if env_example.exists():
            shutil.copy(str(env_example), str(env_file))
            print("✅ Created .env file from template")
            print("⚠️  Please edit .env file with your Pulseway credentials")
        else:
            print("❌ .env.example not found")
            return False
    else:
        print("✅ .env file already exists")

    return True

def build_docker_image():
    """Build the Docker image"""
    print("🔨 Building Docker image...")

    try:
        # Ensure PWD is project root for docker-compose
        project_root = Path(__file__).resolve().parent.parent
        subprocess.run(['docker-compose', '-f', 'docker-compose.yml', 'build'], check=True, cwd=project_root)
        print("✅ Docker image built successfully")
        return True
    except subprocess.CalledProcessError:
        print("❌ Failed to build Docker image")
        return False

def setup_database():
    """Initialize the database"""
    print("🗄️  Setting up database...")

    try:
        # Create database tables by importing the models
        # Assuming script is in backend/, and app is backend/app/
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from app.database import engine
        from app.models.database import Base

        Base.metadata.create_all(bind=engine)
        print("✅ Database tables created")
        return True
    except Exception as e:
        print(f"❌ Failed to setup database: {e}")
        return False

def main():
    """Main setup function"""
    print("🚀 Pulseway Backend Setup")
    print("=" * 40)

    if not check_requirements():
        sys.exit(1)

    create_directories()

    if not setup_environment():
        sys.exit(1)

    if not setup_database():
        print("⚠️  Database setup failed, but continuing...")

    if not build_docker_image():
        sys.exit(1)

    print("\n🎉 Setup completed successfully!")
    print("\nNext steps:")
    print("1. Edit .env file with your Pulseway API credentials")
    print("2. Run: docker-compose up -d")
    print("3. Check status: docker-compose logs -f")
    print("4. Access API docs: http://localhost:8000/docs")

if __name__ == '__main__':
    main()
