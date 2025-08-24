-- Database initialization script for PostgreSQL
-- This script is executed when the Docker container starts

-- Create extensions if needed
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create items table
CREATE TABLE IF NOT EXISTS items (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    price DECIMAL(10, 2) NOT NULL CHECK (price >= 0),
    is_offer BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create index for search functionality
CREATE INDEX IF NOT EXISTS idx_items_name ON items USING gin(to_tsvector('english', name));

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for updated_at
DROP TRIGGER IF EXISTS update_items_updated_at ON items;
CREATE TRIGGER update_items_updated_at
    BEFORE UPDATE ON items
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert some sample data for development
INSERT INTO items (name, price, is_offer) VALUES
    ('Sample Laptop', 999.99, true),
    ('Wireless Mouse', 29.99, false),
    ('USB Keyboard', 49.99, true),
    ('4K Monitor', 299.99, false),
    ('Webcam HD', 79.99, true)
ON CONFLICT DO NOTHING;