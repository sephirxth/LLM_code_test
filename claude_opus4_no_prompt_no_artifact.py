import pygame
import math
import random
import numpy as np
from collections import deque

# 初始化Pygame
pygame.init()

# 常量定义
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60
BACKGROUND_COLOR = (0, 0, 0)
HEPTAGON_COLOR = (255, 255, 255)
HEPTAGON_RADIUS = 300
ROTATION_SPEED = 15  # 度/秒
GRAVITY = 9.81 * 100  # 像素/秒² (放大以适应屏幕)
ELASTICITY = 0.85
BALL_RADIUS = 8
NUM_BALLS = 20
TRAJECTORY_LENGTH = 100

class Ball:
    """球体类，处理球的物理和渲染"""
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-200, 200)  # 像素/秒
        self.vy = random.uniform(-200, 200)
        self.radius = BALL_RADIUS
        self.color = (random.randint(50, 255), 
                     random.randint(50, 255), 
                     random.randint(50, 255))
        self.trajectory = deque(maxlen=TRAJECTORY_LENGTH)
        self.spin = 0  # 自旋角度
        self.spin_speed = random.uniform(-5, 5)  # 自旋速度
        
    def update(self, dt):
        """更新球的位置和速度"""
        # 应用重力
        self.vy += GRAVITY * dt
        
        # 更新位置
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # 更新自旋
        self.spin += self.spin_speed
        
        # 记录轨迹
        self.trajectory.append((int(self.x), int(self.y)))
    
    def draw(self, screen, show_trajectory=True):
        """绘制球体和轨迹"""
        # 绘制轨迹
        if show_trajectory and len(self.trajectory) > 1:
            for i in range(1, len(self.trajectory)):
                alpha = i / len(self.trajectory)
                color = tuple(int(c * alpha) for c in self.color)
                pygame.draw.line(screen, color, 
                               self.trajectory[i-1], 
                               self.trajectory[i], 1)
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, 
                         (int(self.x), int(self.y)), 
                         self.radius)
        
        # 绘制自旋指示器
        spin_x = self.x + self.radius * 0.7 * math.cos(self.spin)
        spin_y = self.y + self.radius * 0.7 * math.sin(self.spin)
        pygame.draw.line(screen, (255, 255, 255), 
                        (self.x, self.y), 
                        (spin_x, spin_y), 2)

class HeptagonSimulation:
    """七边形容器物理模拟主类"""
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("旋转七边形弹跳球模拟")
        self.clock = pygame.time.Clock()
        self.running = True
        self.paused = False
        self.show_trajectory = True
        self.show_fps = True
        
        # 七边形属性
        self.center_x = WINDOW_WIDTH // 2
        self.center_y = WINDOW_HEIGHT // 2
        self.rotation_angle = 0
        
        # 创建球体
        self.balls = []
        self.create_balls()
        
        # 字体
        self.font = pygame.font.Font(None, 36)
        
    def create_balls(self):
        """创建初始球体"""
        self.balls = []
        for _ in range(NUM_BALLS):
            # 在七边形内随机生成位置
            angle = random.uniform(0, 2 * math.pi)
            distance = random.uniform(0, HEPTAGON_RADIUS - BALL_RADIUS - 20)
            x = self.center_x + distance * math.cos(angle)
            y = self.center_y + distance * math.sin(angle)
            self.balls.append(Ball(x, y))
    
    def get_heptagon_vertices(self):
        """获取当前旋转角度下的七边形顶点"""
        vertices = []
        for i in range(7):
            angle = self.rotation_angle + (2 * math.pi * i / 7)
            x = self.center_x + HEPTAGON_RADIUS * math.cos(angle)
            y = self.center_y + HEPTAGON_RADIUS * math.sin(angle)
            vertices.append((x, y))
        return vertices
    
    def point_to_line_distance(self, px, py, x1, y1, x2, y2):
        """计算点到线段的最短距离"""
        line_length = math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
        if line_length == 0:
            return math.sqrt((px - x1)**2 + (py - y1)**2)
        
        t = max(0, min(1, ((px - x1) * (x2 - x1) + (py - y1) * (y2 - y1)) / line_length**2))
        projection_x = x1 + t * (x2 - x1)
        projection_y = y1 + t * (y2 - y1)
        
        return math.sqrt((px - projection_x)**2 + (py - projection_y)**2)
    
    def check_ball_heptagon_collision(self, ball):
        """检查球与七边形边界的碰撞"""
        vertices = self.get_heptagon_vertices()
        
        for i in range(7):
            x1, y1 = vertices[i]
            x2, y2 = vertices[(i + 1) % 7]
            
            # 计算球心到边的距离
            distance = self.point_to_line_distance(ball.x, ball.y, x1, y1, x2, y2)
            
            if distance < ball.radius:
                # 计算边的法向量
                edge_dx = x2 - x1
                edge_dy = y2 - y1
                edge_length = math.sqrt(edge_dx**2 + edge_dy**2)
                edge_dx /= edge_length
                edge_dy /= edge_length
                
                # 法向量（指向内部）
                normal_x = -edge_dy
                normal_y = edge_dx
                
                # 确保法向量指向中心
                to_center_x = self.center_x - ball.x
                to_center_y = self.center_y - ball.y
                if normal_x * to_center_x + normal_y * to_center_y < 0:
                    normal_x = -normal_x
                    normal_y = -normal_y
                
                # 计算相对速度（考虑旋转）
                # 边的切向速度
                mid_x = (x1 + x2) / 2
                mid_y = (y1 + y2) / 2
                r_x = mid_x - self.center_x
                r_y = mid_y - self.center_y
                omega = math.radians(ROTATION_SPEED)
                wall_vx = -omega * r_y
                wall_vy = omega * r_x
                
                # 相对速度
                rel_vx = ball.vx - wall_vx
                rel_vy = ball.vy - wall_vy
                
                # 计算反射速度
                dot_product = rel_vx * normal_x + rel_vy * normal_y
                if dot_product < 0:  # 球正在撞向墙
                    ball.vx = wall_vx + (rel_vx - 2 * dot_product * normal_x) * ELASTICITY
                    ball.vy = wall_vy + (rel_vy - 2 * dot_product * normal_y) * ELASTICITY
                    
                    # 将球推出墙外
                    overlap = ball.radius - distance
                    ball.x += normal_x * overlap * 1.1
                    ball.y += normal_y * overlap * 1.1
                    
                    # 影响自旋
                    ball.spin_speed *= -0.8
    
    def check_ball_ball_collision(self, ball1, ball2):
        """检查并处理球与球之间的碰撞"""
        dx = ball2.x - ball1.x
        dy = ball2.y - ball1.y
        distance = math.sqrt(dx**2 + dy**2)
        
        if distance < ball1.radius + ball2.radius and distance > 0:
            # 标准化碰撞向量
            dx /= distance
            dy /= distance
            
            # 相对速度
            dvx = ball2.vx - ball1.vx
            dvy = ball2.vy - ball1.vy
            dot_product = dvx * dx + dvy * dy
            
            if dot_product < 0:  # 球正在相互接近
                # 计算碰撞后的速度（动量守恒）
                impulse = 2 * dot_product / 2  # 假设质量相等
                
                ball1.vx += impulse * dx * ELASTICITY
                ball1.vy += impulse * dy * ELASTICITY
                ball2.vx -= impulse * dx * ELASTICITY
                ball2.vy -= impulse * dy * ELASTICITY
                
                # 分离球体
                overlap = ball1.radius + ball2.radius - distance
                separation = overlap / 2 * 1.1
                ball1.x -= dx * separation
                ball1.y -= dy * separation
                ball2.x += dx * separation
                ball2.y += dy * separation
                
                # 影响自旋
                ball1.spin_speed += random.uniform(-2, 2)
                ball2.spin_speed += random.uniform(-2, 2)
    
    def update(self, dt):
        """更新模拟状态"""
        if self.paused:
            return
        
        # 更新七边形旋转
        self.rotation_angle += math.radians(ROTATION_SPEED) * dt
        
        # 更新球体
        for ball in self.balls:
            ball.update(dt)
        
        # 检查碰撞
        for ball in self.balls:
            self.check_ball_heptagon_collision(ball)
        
        # 球与球碰撞
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                self.check_ball_ball_collision(self.balls[i], self.balls[j])
    
    def draw(self):
        """绘制所有元素"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # 绘制七边形
        vertices = self.get_heptagon_vertices()
        pygame.draw.polygon(self.screen, HEPTAGON_COLOR, vertices, 3)
        
        # 绘制球体
        for ball in self.balls:
            ball.draw(self.screen, self.show_trajectory)
        
        # 显示FPS
        if self.show_fps:
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", 
                                      True, (255, 255, 0))
            self.screen.blit(fps_text, (10, 10))
        
        # 显示控制说明
        controls = [
            "空格: 暂停/继续",
            "R: 重置",
            "T: 轨迹开关",
            "F: FPS显示",
            "点击: 添加球",
            "ESC: 退出"
        ]
        y_offset = 50
        small_font = pygame.font.Font(None, 24)
        for control in controls:
            text = small_font.render(control, True, (200, 200, 200))
            self.screen.blit(text, (10, y_offset))
            y_offset += 25
        
        # 显示暂停状态
        if self.paused:
            pause_text = self.font.render("暂停", True, (255, 0, 0))
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH//2, 50))
            self.screen.blit(pause_text, text_rect)
        
        pygame.display.flip()
    
    def handle_events(self):
        """处理用户输入事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.create_balls()
                elif event.key == pygame.K_t:
                    self.show_trajectory = not self.show_trajectory
                elif event.key == pygame.K_f:
                    self.show_fps = not self.show_fps
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键点击
                    x, y = pygame.mouse.get_pos()
                    # 检查点击位置是否在七边形内
                    self.balls.append(Ball(x, y))
    
    def run(self):
        """主循环"""
        dt = 0
        while self.running:
            self.handle_events()
            self.update(dt)
            self.draw()
            dt = self.clock.tick(FPS) / 1000.0  # 转换为秒

# 主程序入口
if __name__ == "__main__":
    simulation = HeptagonSimulation()
    simulation.run()
    pygame.quit()