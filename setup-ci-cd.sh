#!/bin/bash

# 🚀 Examify API - CI/CD Setup Script
# This script helps you prepare for committing the new CI/CD pipeline

set -e

echo "🚀 EXAMIFY API - CI/CD SETUP PREPARATION"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Check prerequisites
echo "🔍 CHECKING PREREQUISITES"
echo "========================="
echo ""

# Check if git is available
if command -v git &> /dev/null; then
    print_status "Git is installed"
else
    print_error "Git is not installed. Please install Git first."
    exit 1
fi

# Check if we're in a git repository
if [ -d ".git" ]; then
    print_status "In a Git repository"
else
    print_error "Not in a Git repository. Please run this from your project root."
    exit 1
fi

# Check if Docker is available
if command -v docker &> /dev/null; then
    print_status "Docker is installed"
else
    print_warning "Docker is not installed. Some CI/CD features may not work locally."
fi

# Check if Poetry is available
if command -v poetry &> /dev/null; then
    print_status "Poetry is installed"
else
    print_warning "Poetry is not installed. Please install Poetry for dependency management."
fi

echo ""
echo "📋 CURRENT REPOSITORY STATUS"
echo "============================"
echo ""

# Show current branch
CURRENT_BRANCH=$(git branch --show-current)
print_info "Current branch: $CURRENT_BRANCH"

# Show git status
MODIFIED_FILES=$(git status --porcelain | wc -l)
print_info "Modified/new files: $MODIFIED_FILES"

# Show if there are uncommitted changes
if [ $MODIFIED_FILES -gt 0 ]; then
    print_warning "You have uncommitted changes. Here's what will be committed:"
    echo ""
    git status --short | head -10
    if [ $(git status --porcelain | wc -l) -gt 10 ]; then
        echo "... and $(($MODIFIED_FILES - 10)) more files"
    fi
else
    print_status "Working directory is clean"
fi

echo ""
echo "🔧 CI/CD FILES VERIFICATION"
echo "==========================="
echo ""

# Check if key CI/CD files exist
CI_CD_FILES=(
    ".github/workflows/ci-cd.yml"
    ".github/workflows/pr-validation.yml"
    ".github/workflows/security-monitoring.yml"
    ".github/workflows/performance-monitoring.yml"
    ".github/dependabot.yml"
    "Makefile"
    ".github/README.md"
)

for file in "${CI_CD_FILES[@]}"; do
    if [ -f "$file" ]; then
        print_status "$file exists"
    else
        print_error "$file is missing"
    fi
done

echo ""
echo "⚠️  IMPORTANT SETUP REQUIREMENTS"
echo "================================"
echo ""

print_warning "BEFORE PUSHING TO GITHUB, YOU MUST:"
echo ""
echo "1. 🔑 Configure GitHub Secrets:"
echo "   Go to: Repository Settings > Secrets and variables > Actions"
echo "   Add these required secrets:"
echo "   - AWS_ACCESS_KEY_ID"
echo "   - AWS_SECRET_ACCESS_KEY"
echo "   - AWS_REGION"
echo "   - AWS_APPLICATION_NAME"
echo "   - AWS_ENVIRONMENT_NAME"
echo ""

echo "2. 🛡️  Set up Branch Protection:"
echo "   Go to: Repository Settings > Branches"
echo "   - Add protection rule for 'main' branch"
echo "   - Require PR reviews"
echo "   - Require status checks to pass"
echo ""

echo "3. 🌍 Create Environments:"
echo "   Go to: Repository Settings > Environments"
echo "   - Create 'staging' environment"
echo "   - Create 'production' environment"
echo "   - Configure environment-specific secrets"
echo ""

echo "4. 📦 Optional Integrations:"
echo "   - SLACK_WEBHOOK_URL (for notifications)"
echo "   - SNYK_TOKEN (for enhanced security scanning)"
echo "   - CODECOV_TOKEN (for coverage reporting)"
echo ""

# Ask user if they want to continue
echo ""
read -p "🤔 Have you configured the required GitHub secrets? (y/N): " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    print_warning "Please configure the required secrets before committing."
    print_info "You can still commit to a feature branch for testing, but deployment will fail."
    echo ""
fi

# Suggest commit strategy
echo ""
echo "🎯 RECOMMENDED COMMIT STRATEGY"
echo "============================="
echo ""

if [[ $CURRENT_BRANCH == "main" ]]; then
    print_warning "You're on the main branch!"
    echo ""
    echo "Recommended approach:"
    echo "1. Create a feature branch:"
    echo "   git checkout -b feature/ci-cd-pipeline"
    echo ""
    echo "2. Commit and push to feature branch:"
    echo "   git add ."
    echo "   git commit -m 'feat: implement enterprise-grade CI/CD pipeline'"
    echo "   git push origin feature/ci-cd-pipeline"
    echo ""
    echo "3. Create a Pull Request to test the workflows"
    echo "4. Merge to main when everything works"
    echo ""
else
    print_status "You're on a feature branch ($CURRENT_BRANCH) - good!"
    echo ""
    echo "You can safely commit and push:"
    echo "   git add ."
    echo "   git commit -m 'feat: implement enterprise-grade CI/CD pipeline'"
    echo "   git push origin $CURRENT_BRANCH"
    echo ""
fi

# Show what will happen when they commit
echo ""
echo "📊 WHAT TO EXPECT AFTER COMMIT"
echo "=============================="
echo ""

print_info "When you push, these workflows will trigger:"
echo ""
echo "✅ Immediate (if secrets configured):"
echo "   - Code quality checks (Black, Ruff, MyPy)"
echo "   - Security scanning (Trivy, Semgrep)"
echo "   - Unit tests with coverage"
echo "   - Docker build and scan"
echo ""

echo "⚠️  May fail initially (normal):"
echo "   - AWS deployment steps (if infrastructure not ready)"
echo "   - Some integration tests (if services not configured)"
echo "   - Performance tests (if baseline not established)"
echo ""

echo "🔄 Will run on schedule:"
echo "   - Security monitoring (daily at 2 AM UTC)"
echo "   - Performance testing (weekly on Sundays)"
echo "   - Dependency updates (via Dependabot)"
echo ""

# Final confirmation
echo ""
echo "🚀 READY TO PROCEED?"
echo "==================="
echo ""

read -p "Do you want to proceed with committing the CI/CD pipeline? (y/N): " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    print_status "Great! Here are your next steps:"
    echo ""
    
    if [[ $CURRENT_BRANCH == "main" ]]; then
        echo "1. Create feature branch:"
        echo "   git checkout -b feature/ci-cd-pipeline"
        echo ""
    fi
    
    echo "2. Add all files:"
    echo "   git add ."
    echo ""
    
    echo "3. Commit with descriptive message:"
    echo "   git commit -m 'feat: implement enterprise-grade CI/CD pipeline"
    echo ""
    echo "   - Add comprehensive GitHub Actions workflows"
    echo "   - Implement multi-environment deployment strategy"
    echo "   - Add security scanning and monitoring"
    echo "   - Add performance testing and monitoring"
    echo "   - Add automated dependency management"
    echo "   - Add developer tooling with Makefile"
    echo "   - Add comprehensive documentation'"
    echo ""
    
    echo "4. Push to GitHub:"
    if [[ $CURRENT_BRANCH == "main" ]]; then
        echo "   git push origin feature/ci-cd-pipeline"
    else
        echo "   git push origin $CURRENT_BRANCH"
    fi
    echo ""
    
    echo "5. Monitor the Actions tab in GitHub for workflow results"
    echo ""
    
    print_status "Good luck! 🎉"
else
    print_info "No problem! Take your time to review and prepare."
    echo ""
    echo "📚 Helpful resources:"
    echo "   - Read: COMMIT-EXPECTATIONS.md"
    echo "   - Read: .github/README.md"
    echo "   - Read: CI-CD-TRANSFORMATION.md"
    echo ""
    print_info "Run this script again when you're ready!"
fi

echo ""
echo "📞 Need help? Check the documentation or contact the development team."
echo ""
