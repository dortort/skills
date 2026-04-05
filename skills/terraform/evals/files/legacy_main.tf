provider "aws" {
  region = "us-east-1"
}

terraform {
  required_version = ">= 1.0"
}

resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true

  tags = {
    Name        = "prod-vpc"
    Environment = "production"
  }
}

resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  availability_zone       = "us-east-1a"
  map_public_ip_on_launch = true

  tags = {
    Name = "prod-public-subnet"
  }
}

resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "us-east-1b"

  tags = {
    Name = "prod-private-subnet"
  }
}

resource "aws_security_group" "app" {
  name        = "prod-app-sg"
  description = "Security group for app server"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    from_port   = 8080
    to_port     = 8080
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "prod-app-sg"
  }
}

resource "aws_security_group" "db" {
  name        = "prod-db-sg"
  description = "Security group for RDS"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "prod-db-sg"
  }
}

resource "aws_db_subnet_group" "main" {
  name       = "prod-db-subnet-group"
  subnet_ids = [aws_subnet.public.id, aws_subnet.private.id]

  tags = {
    Name = "prod-db-subnet-group"
  }
}

resource "aws_db_instance" "postgres" {
  identifier             = "prod-postgres"
  engine                 = "postgres"
  engine_version         = "15.4"
  instance_class         = "db.t3.medium"
  allocated_storage      = 20
  storage_type           = "gp3"
  db_name                = "appdb"
  username               = "admin"
  password               = "supersecretpassword123"
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  skip_final_snapshot    = true
  multi_az               = false

  tags = {
    Name        = "prod-postgres"
    Environment = "production"
  }
}

resource "aws_instance" "app" {
  ami                    = "ami-0c55b159cbfafe1f0"
  instance_type          = "t3.medium"
  subnet_id              = aws_subnet.public.id
  vpc_security_group_ids = [aws_security_group.app.id]

  tags = {
    Name        = "prod-app-server"
    Environment = "production"
  }
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "app_public_ip" {
  value = aws_instance.app.public_ip
}

output "db_endpoint" {
  value = aws_db_instance.postgres.endpoint
}
