#!/bin/bash
python proxycache.py&
http_proxy=localhost:8000 python builder.py
