# 🚀 Examify API - CI/CD Pipeline Documentation

This document describes the comprehensive CI/CD pipeline for the Examify API, designed to ensure code quality, security, and reliable deployments.

## 📋 Table of Contents

- [Overview](#overview)
- [Workflows](#workflows)
- [Setup Requirements](#setup-requirements)
- [Environment Configuration](#environment-configuration)
- [Quality Gates](#quality-gates)
- [Security Measures](#security-measures)
- [Deployment Strategy](#deployment-strategy)
- [Monitoring & Alerts](#monitoring--alerts)
- [Troubleshooting](#troubleshooting)

## 🎯 Overview

Our CI/CD pipeline follows industry best practices and includes:

- **Automated Testing** - Unit, integration, and performance tests
- **Code Quality Checks** - Linting, formatting, and type checking
- **Security Scanning** - Vulnerability detection and secret scanning
- **Multi-Environment Deployment** - Staging and production environments
- **Performance Monitoring** - Load testing and regression detection
- **Automated Dependency Management** - Security updates and license compliance

## 🔄 Workflows

### 1. Main CI/CD Pipeline (`ci-cd.yml`)

**Triggers:**
- Push to `main` or `develop` branches
- Tags starting with `v*`
- Pull requests to `main` or `develop`

**Jobs:**
1. **Code Quality & Security** - Linting, formatting, type checking, security scans
2. **Testing Suite** - Unit tests with PostgreSQL and Redis services
3. **Docker Build & Security Scan** - Multi-platform builds with vulnerability scanning
4. **Integration Tests** - End-to-end testing with Docker Compose
5. **Deploy to Staging** - Automatic deployment on `develop` branch
6. **Deploy to Production** - Automatic deployment on version tags

### 2. Pull Request Validation (`pr-validation.yml`)

**Triggers:**
- Pull request events (opened, synchronized, reopened)

**Features:**
- PR title validation (semantic commits)
- PR size validation
- Fast quality checks
- Security scanning
- Unit tests with coverage reporting
- Docker build testing
- Automated Dependabot PR merging

### 3. Security Monitoring (`security-monitoring.yml`)

**Triggers:**
- Daily schedule (2 AM UTC)
- Manual dispatch
- Changes to dependency files

**Features:**
- Dependency vulnerability scanning
- License compliance checking
- Secret detection
- Docker image security scanning
- Automated dependency update PRs

### 4. Performance Monitoring (`performance-monitoring.yml`)

**Triggers:**
- Weekly schedule (Sundays 3 AM UTC)
- Manual dispatch with parameters

**Features:**
- API load testing with Locust
- Database performance testing
- Memory and CPU profiling
- Performance regression detection

## ⚙️ Setup Requirements

### GitHub Secrets

Configure the following secrets in your GitHub repository:

#### AWS Deployment
```
AWS_ACCESS_KEY_ID          # AWS access key for ECR and ECS
AWS_SECRET_ACCESS_KEY      # AWS secret key
AWS_REGION                 # AWS region (e.g., us-east-1)
AWS_APPLICATION_NAME       # Elastic Beanstalk application name
AWS_ENVIRONMENT_NAME       # Elastic Beanstalk environment name
```

#### Optional Integrations
```
SNYK_TOKEN                 # Snyk security scanning token
SLACK_WEBHOOK_URL          # Slack notifications webhook
CODECOV_TOKEN              # Codecov integration token
```

### Repository Settings

1. **Branch Protection Rules:**
   - Require PR reviews for `main` branch
   - Require status checks to pass
   - Require branches to be up to date
   - Restrict pushes to `main` branch

2. **Environments:**
   - Create `staging` and `production` environments
   - Configure environment-specific secrets
   - Set up deployment approval requirements for production

## 🌍 Environment Configuration

### Development Environment
- **Branch:** Any feature branch
- **Database:** Local PostgreSQL container
- **Redis:** Local Redis container
- **Deployment:** Local Docker Compose

### Staging Environment
- **Branch:** `develop`
- **Database:** AWS RDS (staging instance)
- **Redis:** AWS ElastiCache (staging cluster)
- **Deployment:** AWS ECS (staging cluster)

### Production Environment
- **Branch:** Version tags (`v*`)
- **Database:** AWS RDS (production instance)
- **Redis:** AWS ElastiCache (production cluster)
- **Deployment:** AWS ECS (production cluster)

## ✅ Quality Gates

All code must pass these quality gates before deployment:

### Code Quality
- ✅ **Black** formatting compliance
- ✅ **Ruff** linting (no errors)
- ✅ **MyPy** type checking (no errors)
- ✅ **Import sorting** with isort

### Testing
- ✅ **Unit tests** pass (>80% coverage)
- ✅ **Integration tests** pass
- ✅ **API endpoint tests** pass
- ✅ **Database connectivity** verified

### Security
- ✅ **Bandit** security scan (no high/critical issues)
- ✅ **Trivy** vulnerability scan (no critical vulnerabilities)
- ✅ **Secret detection** (no exposed secrets)
- ✅ **Dependency audit** (no known vulnerabilities)

### Performance
- ✅ **Docker build** successful
- ✅ **Container startup** under 30 seconds
- ✅ **API response time** under 1 second average
- ✅ **Memory usage** within limits

## 🔒 Security Measures

### Automated Security Scanning
- **Daily vulnerability scans** of dependencies
- **Container image scanning** with Trivy
- **Secret detection** with TruffleHog and GitLeaks
- **License compliance** checking
- **SAST scanning** with Semgrep

### Security Policies
- **Dependency updates** via automated PRs
- **Security patches** prioritized for immediate deployment
- **Container base images** regularly updated
- **Access tokens** rotated regularly

### Compliance
- **OWASP Top 10** security checks
- **License compatibility** verification
- **Audit trail** for all deployments
- **Security incident** response procedures

## 🚀 Deployment Strategy

### Staging Deployment
1. **Trigger:** Push to `develop` branch
2. **Process:**
   - Build and push Docker images to ECR
   - Update ECS service with new image
   - Run smoke tests
   - Notify team of deployment

### Production Deployment
1. **Trigger:** Push version tag (e.g., `v1.2.3`)
2. **Process:**
   - All quality gates must pass
   - Manual approval required (if configured)
   - Blue-green deployment to production ECS
   - Health checks and rollback capability
   - Create GitHub release with changelog

### Rollback Strategy
- **Automatic rollback** on health check failures
- **Manual rollback** via GitHub Actions
- **Database migrations** handled separately
- **Zero-downtime deployments** with ECS

## 📊 Monitoring & Alerts

### Performance Monitoring
- **Weekly load tests** with configurable parameters
- **Database performance** benchmarking
- **Memory and CPU profiling**
- **Response time tracking**

### Alert Conditions
- **Security vulnerabilities** detected
- **Test failures** in main branch
- **Deployment failures**
- **Performance regressions**

### Notification Channels
- **GitHub Issues** for security alerts
- **Slack notifications** for deployment status
- **Email alerts** for critical failures
- **Dashboard updates** for metrics

## 🔧 Local Development

### Quick Start
```bash
# Install dependencies
make install

# Run quality checks
make quality

# Run tests
make test-cov

# Start development environment
make run-dev

# Run pre-commit checks
make pre-commit
```

### Available Commands
See the [Makefile](../Makefile) for all available development commands.

## 🐛 Troubleshooting

### Common Issues

#### 1. Docker Build Failures
```bash
# Clear Docker cache
docker system prune -f
make clean

# Rebuild with no cache
docker compose build --no-cache
```

#### 2. Test Failures
```bash
# Run tests with verbose output
make test

# Check test environment
make env-check

# Reset test database
make clear-db
make init-db
```

#### 3. Deployment Issues
```bash
# Check AWS credentials
aws sts get-caller-identity

# Verify ECR login
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account>.dkr.ecr.us-east-1.amazonaws.com

# Check ECS service status
aws ecs describe-services --cluster examify-production --services examify-api-production
```

#### 4. Performance Issues
```bash
# Run local performance test
make perf-test

# Check container resources
docker stats

# Profile application
make profile
```

### Getting Help

1. **Check workflow logs** in GitHub Actions
2. **Review error messages** in the pipeline
3. **Consult this documentation**
4. **Contact the development team**

## 📚 Additional Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
- [AWS ECS Documentation](https://docs.aws.amazon.com/ecs/)
- [GitHub Actions Documentation](https://docs.github.com/en/actions)

## 🤝 Contributing

When contributing to the CI/CD pipeline:

1. **Test changes locally** first
2. **Update documentation** as needed
3. **Follow semantic commit** conventions
4. **Ensure all quality gates** pass
5. **Get peer review** for pipeline changes

---

**Last Updated:** $(date)
**Pipeline Version:** 2.0
**Maintained by:** Examify Development Team
