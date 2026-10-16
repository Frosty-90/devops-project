#!/usr/bin/env bash
# Load sample inventory. Usage: URL=http://<host> ./scripts/seed.sh
set -euo pipefail
URL="${URL:-http://localhost:3000}"
add() { curl -s -o /dev/null -w "%{http_code} $1\n" -X POST "$URL/api/products" -H 'Content-Type: application/json' -d "$2"; }
add KB-001  '{"sku":"KB-001","name":"Mechanical keyboard","category":"Peripherals","supplier":"Keychron","quantity":42,"reorder_level":10,"unit_price":6499}'
add MS-002  '{"sku":"MS-002","name":"Wireless mouse","category":"Peripherals","supplier":"Logitech","quantity":8,"reorder_level":15,"unit_price":1899}'
add MN-003  '{"sku":"MN-003","name":"27\" 4K monitor","category":"Displays","supplier":"Dell","quantity":12,"reorder_level":5,"unit_price":28999}'
add CB-004  '{"sku":"CB-004","name":"USB-C cable 2m","category":"Accessories","supplier":"Anker","quantity":0,"reorder_level":25,"unit_price":799}'
add HD-005  '{"sku":"HD-005","name":"Noise-cancelling headset","category":"Audio","supplier":"Sony","quantity":17,"reorder_level":6,"unit_price":24990}'
add DK-006  '{"sku":"DK-006","name":"Laptop docking station","category":"Accessories","supplier":"Lenovo","quantity":4,"reorder_level":4,"unit_price":15499}'
add WC-007  '{"sku":"WC-007","name":"1080p webcam","category":"Peripherals","supplier":"Logitech","quantity":30,"reorder_level":8,"unit_price":4599}'
