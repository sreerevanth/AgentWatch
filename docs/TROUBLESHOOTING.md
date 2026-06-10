# Troubleshooting Guide

This document helps resolve common setup, installation, and runtime issues in AgentWatch.

---

## 1. Environment Setup Issues

### ❌ Missing `.env` file

**Problem:**
Application fails to start with missing configuration errors.

**Solution:**

Copy the example environment file:

```bash
cp .env.example .env