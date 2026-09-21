#!/usr/bin/env python3
"""
ADVANCED GAME GENERATOR
Generates games from simple math to complex Atari/Apple 2 style games
Progressive complexity: Math → Logic → Arcade → Retro → Classic
"""

import os
import json
import random

class AdvancedGameGenerator:
    def __init__(self):
        self.system_name = "AdvancedGameGenerator"
        self.version = "1.0_progressive_complexity"
        
        print("🎮 ADVANCED GAME GENERATOR INITIALIZED")
        print("📈 Progressive complexity: Math → Logic → Arcade → Retro → Classic")
    
    def generate_math_game(self, app_path, description):
        """Generate Level 1: Math games"""
        if 'addition' in description.lower():
            return self.generate_addition_game(app_path)
        elif 'multiplication' in description.lower():
            return self.generate_multiplication_game(app_path)
        else:
            return self.generate_number_guessing_game(app_path)
    
    def generate_addition_game(self, app_path):
        """Generate simple addition math game"""
        server_js = self.get_basic_server()
        
        index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Addition Math Game</title>
    <style>
        body { 
            font-family: Arial, sans-serif; 
            display: flex; 
            justify-content: center; 
            align-items: center; 
            min-height: 100vh; 
            margin: 0; 
            background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        }
        .game-container { 
            text-align: center; 
            background: white; 
            padding: 40px; 
            border-radius: 20px; 
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            min-width: 400px;
        }
        .problem { 
            font-size: 48px; 
            font-weight: bold; 
            margin: 30px 0;
            color: #2c3e50;
        }
        .answer-input { 
            font-size: 36px; 
            padding: 15px; 
            width: 200px; 
            text-align: center; 
            border: 3px solid #3498db; 
            border-radius: 10px;
            margin: 20px;
        }
        .btn { 
            padding: 15px 30px; 
            font-size: 20px; 
            background: #27ae60; 
            color: white; 
            border: none; 
            border-radius: 10px; 
            cursor: pointer; 
            margin: 10px;
        }
        .btn:hover { background: #219a52; transform: scale(1.05); }
        .score { 
            font-size: 24px; 
            font-weight: bold; 
            margin: 20px 0;
            color: #e74c3c;
        }
        .feedback { 
            font-size: 18px; 
            margin: 15px 0;
            min-height: 25px;
        }
        .correct { color: #27ae60; }
        .incorrect { color: #e74c3c; }
    </style>
</head>
<body>
    <div class="game-container">
        <h1>🧮 Addition Game</h1>
        <div class="score">Score: <span id="score">0</span> / <span id="total">0</span></div>
        <div class="problem" id="problem">5 + 3 = ?</div>
        <input type="number" class="answer-input" id="answer" placeholder="?" autofocus>
        <br>
        <button class="btn" onclick="checkAnswer()">Check Answer</button>
        <button class="btn" onclick="newProblem()">New Problem</button>
        <div class="feedback" id="feedback"></div>
    </div>

    <script>
        let currentA, currentB, correctAnswer;
        let score = 0;
        let total = 0;

        function generateProblem() {
            currentA = Math.floor(Math.random() * 50) + 1;
            currentB = Math.floor(Math.random() * 50) + 1;
            correctAnswer = currentA + currentB;
            
            document.getElementById('problem').textContent = `${currentA} + ${currentB} = ?`;
            document.getElementById('answer').value = '';
            document.getElementById('answer').focus();
            document.getElementById('feedback').textContent = '';
        }

        function checkAnswer() {
            const userAnswer = parseInt(document.getElementById('answer').value);
            const feedbackEl = document.getElementById('feedback');
            
            total++;
            
            if (userAnswer === correctAnswer) {
                score++;
                feedbackEl.textContent = '🎉 Correct! Great job!';
                feedbackEl.className = 'feedback correct';
                setTimeout(newProblem, 1500);
            } else {
                feedbackEl.textContent = `❌ Incorrect. The answer is ${correctAnswer}`;
                feedbackEl.className = 'feedback incorrect';
            }
            
            document.getElementById('score').textContent = score;
            document.getElementById('total').textContent = total;
        }

        function newProblem() {
            generateProblem();
        }

        // Handle Enter key
        document.getElementById('answer').addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                checkAnswer();
            }
        });

        // Start first problem
        generateProblem();
    </script>
</body>
</html>'''
        
        return self.save_app_files(app_path, server_js, index_html, {
            "express": "^4.18.2"
        })
    
    def generate_snake_game(self, app_path):
        """Generate Level 3: Snake arcade game"""
        server_js = self.get_basic_server()
        
        index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Snake Game</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 100%);
            font-family: 'Courier New', monospace;
            color: #00ff41;
        }
        .game-container {
            text-align: center;
            background: rgba(0, 0, 0, 0.8);
            padding: 20px;
            border: 2px solid #00ff41;
            border-radius: 10px;
            box-shadow: 0 0 20px #00ff41;
        }
        #gameCanvas {
            border: 2px solid #00ff41;
            background: #000;
        }
        .score {
            font-size: 24px;
            margin: 10px 0;
            text-shadow: 0 0 10px #00ff41;
        }
        .controls {
            margin: 15px 0;
            font-size: 14px;
            opacity: 0.8;
        }
        .game-over {
            color: #ff0041;
            font-size: 20px;
            font-weight: bold;
            margin: 10px 0;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1>🐍 SNAKE GAME</h1>
        <div class="score">Score: <span id="score">0</span> | High Score: <span id="highScore">0</span></div>
        <canvas id="gameCanvas" width="400" height="400"></canvas>
        <div class="controls">Use ARROW KEYS to control the snake</div>
        <div id="gameOver" class="game-over" style="display: none;">
            GAME OVER! Press SPACE to restart
        </div>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const highScoreElement = document.getElementById('highScore');
        const gameOverElement = document.getElementById('gameOver');

        const gridSize = 20;
        const tileCount = canvas.width / gridSize;

        let snake = [
            {x: 10, y: 10}
        ];
        let food = {x: 15, y: 15};
        let dx = 0;
        let dy = 0;
        let score = 0;
        let highScore = localStorage.getItem('snakeHighScore') || 0;
        let gameRunning = false;

        highScoreElement.textContent = highScore;

        function drawGame() {
            clearCanvas();
            moveSnake();
            drawFood();
            drawSnake();
            checkGameEnd();
        }

        function clearCanvas() {
            ctx.fillStyle = 'black';
            ctx.fillRect(0, 0, canvas.width, canvas.height);
        }

        function drawSnake() {
            ctx.fillStyle = '#00ff41';
            for (let part of snake) {
                ctx.fillRect(part.x * gridSize, part.y * gridSize, gridSize - 2, gridSize - 2);
            }
        }

        function moveSnake() {
            const head = {x: snake[0].x + dx, y: snake[0].y + dy};
            snake.unshift(head);

            if (head.x === food.x && head.y === food.y) {
                score++;
                scoreElement.textContent = score;
                generateFood();
            } else {
                snake.pop();
            }
        }

        function drawFood() {
            ctx.fillStyle = '#ff0041';
            ctx.fillRect(food.x * gridSize, food.y * gridSize, gridSize - 2, gridSize - 2);
        }

        function generateFood() {
            food = {
                x: Math.floor(Math.random() * tileCount),
                y: Math.floor(Math.random() * tileCount)
            };
        }

        function checkGameEnd() {
            for (let i = 4; i < snake.length; i++) {
                if (snake[i].x === snake[0].x && snake[i].y === snake[0].y) {
                    gameOver();
                    return;
                }
            }

            const hitLeftWall = snake[0].x < 0;
            const hitRightWall = snake[0].x >= tileCount;
            const hitTopWall = snake[0].y < 0;
            const hitBottomWall = snake[0].y >= tileCount;

            if (hitLeftWall || hitRightWall || hitTopWall || hitBottomWall) {
                gameOver();
            }
        }

        function gameOver() {
            if (score > highScore) {
                highScore = score;
                highScoreElement.textContent = highScore;
                localStorage.setItem('snakeHighScore', highScore);
            }
            
            gameRunning = false;
            gameOverElement.style.display = 'block';
        }

        function resetGame() {
            snake = [{x: 10, y: 10}];
            food = {x: 15, y: 15};
            dx = 0;
            dy = 0;
            score = 0;
            scoreElement.textContent = score;
            gameOverElement.style.display = 'none';
            gameRunning = true;
        }

        document.addEventListener('keydown', (e) => {
            if (!gameRunning) {
                if (e.code === 'Space') {
                    resetGame();
                }
                return;
            }

            const LEFT_KEY = 37;
            const RIGHT_KEY = 39;
            const UP_KEY = 38;
            const DOWN_KEY = 40;

            const keyPressed = e.keyCode;
            const goingUp = dy === -1;
            const goingDown = dy === 1;
            const goingRight = dx === 1;
            const goingLeft = dx === -1;

            if (keyPressed === LEFT_KEY && !goingRight) {
                dx = -1;
                dy = 0;
            }
            if (keyPressed === UP_KEY && !goingDown) {
                dx = 0;
                dy = -1;
            }
            if (keyPressed === RIGHT_KEY && !goingLeft) {
                dx = 1;
                dy = 0;
            }
            if (keyPressed === DOWN_KEY && !goingUp) {
                dx = 0;
                dy = 1;
            }
        });

        // Auto-start the game
        setTimeout(() => {
            resetGame();
            setInterval(drawGame, 100);
        }, 1000);
    </script>
</body>
</html>'''
        
        return self.save_app_files(app_path, server_js, index_html, {
            "express": "^4.18.2"
        })
    
    def generate_breakout_game(self, app_path):
        """Generate Level 3: Breakout arcade game"""
        server_js = self.get_basic_server()
        
        index_html = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Breakout Game</title>
    <style>
        body {
            display: flex;
            justify-content: center;
            align-items: center;
            min-height: 100vh;
            margin: 0;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: Arial, sans-serif;
        }
        .game-container {
            text-align: center;
            background: rgba(0, 0, 0, 0.8);
            padding: 20px;
            border-radius: 15px;
            color: white;
        }
        #gameCanvas {
            border: 3px solid white;
            border-radius: 5px;
            background: #1a1a1a;
        }
        .score {
            font-size: 24px;
            margin: 10px 0;
        }
        .controls {
            margin: 10px 0;
            font-size: 14px;
            opacity: 0.8;
        }
    </style>
</head>
<body>
    <div class="game-container">
        <h1>🧱 BREAKOUT</h1>
        <div class="score">Score: <span id="score">0</span> | Lives: <span id="lives">3</span></div>
        <canvas id="gameCanvas" width="600" height="400"></canvas>
        <div class="controls">Move mouse to control paddle | Click to start ball</div>
    </div>

    <script>
        const canvas = document.getElementById('gameCanvas');
        const ctx = canvas.getContext('2d');
        const scoreElement = document.getElementById('score');
        const livesElement = document.getElementById('lives');

        // Game variables
        let score = 0;
        let lives = 3;
        
        // Ball
        let ballX = canvas.width / 2;
        let ballY = canvas.height - 50;
        let ballDX = 3;
        let ballDY = -3;
        let ballRadius = 8;
        let ballActive = false;

        // Paddle
        let paddleWidth = 100;
        let paddleHeight = 12;
        let paddleX = (canvas.width - paddleWidth) / 2;
        let paddleY = canvas.height - 20;

        // Bricks
        let brickRows = 6;
        let brickCols = 10;
        let brickWidth = 55;
        let brickHeight = 20;
        let brickPadding = 3;
        let brickOffsetTop = 50;
        let brickOffsetLeft = 30;
        let bricks = [];

        // Initialize bricks
        for (let r = 0; r < brickRows; r++) {
            bricks[r] = [];
            for (let c = 0; c < brickCols; c++) {
                bricks[r][c] = { x: 0, y: 0, status: 1 };
            }
        }

        function drawBall() {
            ctx.beginPath();
            ctx.arc(ballX, ballY, ballRadius, 0, Math.PI * 2);
            ctx.fillStyle = "#fff";
            ctx.fill();
            ctx.closePath();
        }

        function drawPaddle() {
            ctx.beginPath();
            ctx.rect(paddleX, paddleY, paddleWidth, paddleHeight);
            ctx.fillStyle = "#0095DD";
            ctx.fill();
            ctx.closePath();
        }

        function drawBricks() {
            for (let r = 0; r < brickRows; r++) {
                for (let c = 0; c < brickCols; c++) {
                    if (bricks[r][c].status === 1) {
                        let brickX = c * (brickWidth + brickPadding) + brickOffsetLeft;
                        let brickY = r * (brickHeight + brickPadding) + brickOffsetTop;
                        bricks[r][c].x = brickX;
                        bricks[r][c].y = brickY;
                        
                        ctx.beginPath();
                        ctx.rect(brickX, brickY, brickWidth, brickHeight);
                        
                        // Different colors for different rows
                        const colors = ['#e74c3c', '#e67e22', '#f1c40f', '#2ecc71', '#3498db', '#9b59b6'];
                        ctx.fillStyle = colors[r];
                        ctx.fill();
                        ctx.closePath();
                    }
                }
            }
        }

        function collisionDetection() {
            for (let r = 0; r < brickRows; r++) {
                for (let c = 0; c < brickCols; c++) {
                    let brick = bricks[r][c];
                    if (brick.status === 1) {
                        if (ballX > brick.x && ballX < brick.x + brickWidth &&
                            ballY > brick.y && ballY < brick.y + brickHeight) {
                            ballDY = -ballDY;
                            brick.status = 0;
                            score++;
                            scoreElement.textContent = score;
                            
                            // Check if all bricks are destroyed
                            if (score === brickRows * brickCols) {
                                alert("YOU WIN! CONGRATULATIONS!");
                                document.location.reload();
                            }
                        }
                    }
                }
            }
        }

        function draw() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            
            drawBricks();
            drawBall();
            drawPaddle();
            collisionDetection();

            if (ballActive) {
                // Ball collision with walls
                if (ballX + ballDX > canvas.width - ballRadius || ballX + ballDX < ballRadius) {
                    ballDX = -ballDX;
                }
                if (ballY + ballDY < ballRadius) {
                    ballDY = -ballDY;
                } else if (ballY + ballDY > canvas.height - ballRadius) {
                    // Ball hit bottom
                    if (ballX > paddleX && ballX < paddleX + paddleWidth) {
                        ballDY = -ballDY;
                    } else {
                        lives--;
                        livesElement.textContent = lives;
                        if (lives === 0) {
                            alert("GAME OVER");
                            document.location.reload();
                        } else {
                            ballX = canvas.width / 2;
                            ballY = canvas.height - 50;
                            ballDX = 3;
                            ballDY = -3;
                            paddleX = (canvas.width - paddleWidth) / 2;
                            ballActive = false;
                        }
                    }
                }

                ballX += ballDX;
                ballY += ballDY;
            } else {
                // Ball follows paddle when inactive
                ballX = paddleX + paddleWidth / 2;
            }
        }

        // Mouse controls
        document.addEventListener("mousemove", function(e) {
            let relativeX = e.clientX - canvas.offsetLeft;
            if (relativeX > 0 && relativeX < canvas.width) {
                paddleX = relativeX - paddleWidth / 2;
            }
        });

        // Click to start ball
        canvas.addEventListener("click", function() {
            if (!ballActive) {
                ballActive = true;
            }
        });

        // Game loop
        setInterval(draw, 10);
    </script>
</body>
</html>'''
        
        return self.save_app_files(app_path, server_js, index_html, {
            "express": "^4.18.2"
        })
    
    def generate_game_by_level(self, level, app_path, description):
        """Generate game based on complexity level"""
        if level == 'level_1_math':
            return self.generate_math_game(app_path, description)
        elif level == 'level_2_logic':
            return self.generate_tic_tac_toe(app_path)
        elif level == 'level_3_arcade':
            if 'snake' in description.lower():
                return self.generate_snake_game(app_path)
            else:
                return self.generate_breakout_game(app_path)
        elif level == 'level_4_retro':
            return self.generate_space_invaders(app_path)
        elif level == 'level_5_classic':
            return self.generate_text_adventure(app_path)
        else:
            return self.generate_math_game(app_path, description)
    
    def generate_tic_tac_toe(self, app_path):
        """Generate tic tac toe for logic level"""
        # Use the existing tic tac toe from functional_app_generator
        from functional_app_generator import FunctionalAppGenerator
        generator = FunctionalAppGenerator()
        return generator.generate_tic_tac_toe(app_path, "tic tac toe game")
    
    def save_app_files(self, app_path, server_js, index_html, dependencies):
        """Save all app files"""
        os.makedirs(app_path, exist_ok=True)
        os.makedirs(os.path.join(app_path, 'public'), exist_ok=True)
        
        with open(os.path.join(app_path, 'server.js'), 'w') as f:
            f.write(server_js)
        
        with open(os.path.join(app_path, 'public', 'index.html'), 'w') as f:
            f.write(index_html)
        
        package_json = {
            "name": os.path.basename(app_path).replace('_', '-'),
            "version": "1.0.0",
            "description": "AI-generated game",
            "main": "server.js",
            "scripts": {"start": "node server.js"},
            "dependencies": dependencies
        }
        
        with open(os.path.join(app_path, 'package.json'), 'w') as f:
            json.dump(package_json, f, indent=2)
        
        return {'files_created': 3, 'functional': True, 'testable': True}
    
    def get_basic_server(self):
        """Get basic server template"""
        return '''const express = require('express');
const path = require('path');
const net = require('net');

const app = express();

function findAvailablePort(startPort = 3000, maxPort = 3100) {
  return new Promise((resolve, reject) => {
    function tryPort(port) {
      if (port > maxPort) {
        reject(new Error('No available ports found'));
        return;
      }
      const server = net.createServer();
      server.listen(port, () => {
        server.once('close', () => resolve(port));
        server.close();
      });
      server.on('error', () => {
        tryPort(port + 1);
      });
    }
    tryPort(startPort);
  });
}

app.use(express.static('public'));
app.get('/', (req, res) => {
  res.sendFile(path.join(__dirname, 'public', 'index.html'));
});

async function startServer() {
  try {
    const PORT = process.env.PORT || await findAvailablePort(3000);
    app.listen(PORT, () => {
      console.log(`🎮 Game running on http://localhost:${PORT}`);
      console.log(`💡 Port: ${PORT}`);
    });
  } catch (error) {
    console.error('❌ Could not start server:', error.message);
    process.exit(1);
  }
}

startServer();
'''

if __name__ == "__main__":
    generator = AdvancedGameGenerator()
    print("🎮 ADVANCED GAME GENERATOR READY")
    print("📈 Math → Logic → Arcade → Retro → Classic progression")