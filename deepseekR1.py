import pygame
import sys
import math
import random
import numpy as np

# 初始化pygame
pygame.init()

# 屏幕设置
WIDTH, HEIGHT = 800, 800
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("旋转七边形中的弹跳球")

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)

# 物理参数
FPS = 60
GRAVITY = 9.81 * 100  # 转换为像素/秒² (1米 = 100像素)
ELASTICITY = 0.85
BALL_RADIUS = 8
ROTATION_SPEED = 15  # 度/秒 (顺时针)

# 七边形参数
HEPTAGON_RADIUS = 300
CENTER = (WIDTH // 2, HEIGHT // 2)

class Ball:
    def __init__(self, x, y, vx, vy, color):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.radius = BALL_RADIUS
        self.color = color
        self.trail = []  # 轨迹存储
        self.trail_length = 100  # 轨迹长度
    
    def update(self, dt):
        # 应用重力
        self.vy += GRAVITY * dt
        
        # 更新位置
        self.x += self.vx * dt
        self.y += self.vy * dt
        
        # 更新轨迹
        self.trail.append((self.x, self.y))
        if len(self.trail) > self.trail_length:
            self.trail.pop(0)
    
    def draw(self, surface):
        # 绘制轨迹
        for i, (trail_x, trail_y) in enumerate(self.trail):
            alpha = int(255 * i / len(self.trail))
            color = (self.color[0], self.color[1], self.color[2], alpha)
            pygame.draw.circle(surface, color, (int(trail_x), int(trail_y)), max(1, self.radius // 3))
        
        # 绘制球体
        pygame.draw.circle(surface, self.color, (int(self.x), int(self.y)), self.radius)
        
        # 绘制自旋效果
        spin_angle = pygame.time.get_ticks() / 20 % 360
        spin_x = self.x + math.cos(math.radians(spin_angle)) * self.radius * 0.7
        spin_y = self.y + math.sin(math.radians(spin_angle)) * self.radius * 0.7
        pygame.draw.circle(surface, WHITE, (int(spin_x), int(spin_y)), self.radius // 3)

class Heptagon:
    def __init__(self, center, radius):
        self.center = center
        self.radius = radius
        self.rotation_angle = 0  # 当前旋转角度 (度)
        self.vertices = self.calculate_vertices()
    
    def calculate_vertices(self):
        vertices = []
        for i in range(7):
            angle = math.radians(self.rotation_angle + i * 360 / 7)
            x = self.center[0] + self.radius * math.cos(angle)
            y = self.center[1] + self.radius * math.sin(angle)
            vertices.append((x, y))
        return vertices
    
    def update(self, dt):
        # 更新旋转角度 (顺时针)
        self.rotation_angle -= ROTATION_SPEED * dt
        self.vertices = self.calculate_vertices()
    
    def draw(self, surface):
        pygame.draw.polygon(surface, WHITE, self.vertices, 2)
        
        # 绘制旋转中心
        pygame.draw.circle(surface, (255, 0, 0), (int(self.center[0]), int(self.center[1])), 5)
    
    def distance_to_edge(self, point, edge_idx):
        """计算点到边的距离和最近点"""
        p1 = np.array(self.vertices[edge_idx])
        p2 = np.array(self.vertices[(edge_idx + 1) % 7])
        p = np.array(point)
        
        edge = p2 - p1
        edge_length = np.linalg.norm(edge)
        edge_unit = edge / edge_length
        
        # 计算投影点
        t = np.dot(p - p1, edge_unit)
        t = max(0, min(edge_length, t))
        projection = p1 + t * edge_unit
        
        # 计算距离和法向量
        distance = np.linalg.norm(p - projection)
        normal = (p - projection) / distance if distance > 0 else np.array([0, 0])
        
        return distance, projection, normal
    
    def check_collision(self, ball):
        """检测球与七边形边界的碰撞"""
        for i in range(7):
            distance, closest_point, normal = self.distance_to_edge((ball.x, ball.y), i)
            
            # 如果球与边的距离小于球的半径，发生碰撞
            if distance < ball.radius:
                # 计算球心到碰撞点的向量
                collision_vector = np.array([ball.x - closest_point[0], 
                                            ball.y - closest_point[1]])
                
                # 计算球的速度在法线方向的分量
                velocity = np.array([ball.vx, ball.vy])
                normal_component = np.dot(velocity, normal)
                
                # 仅当球向边界移动时响应碰撞
                if normal_component < 0:
                    # 更新球的位置，防止陷入边界
                    overlap = ball.radius - distance
                    ball.x += normal[0] * overlap * 1.1
                    ball.y += normal[1] * overlap * 1.1
                    
                    # 计算反弹后的速度 (考虑弹性系数)
                    tangent = np.array([-normal[1], normal[0]])
                    tangent_component = np.dot(velocity, tangent)
                    
                    # 应用反弹 (保留切向速度，反转法向速度并应用弹性系数)
                    new_normal_component = -normal_component * ELASTICITY
                    ball.vx = tangent[0] * tangent_component + normal[0] * new_normal_component
                    ball.vy = tangent[1] * tangent_component + normal[1] * new_normal_component
                    
                    return True
        return False

def check_ball_collision(ball1, ball2):
    """检测和处理两个球之间的碰撞"""
    dx = ball2.x - ball1.x
    dy = ball2.y - ball1.y
    distance = math.sqrt(dx**2 + dy**2)
    
    # 如果两球重叠
    if distance < ball1.radius + ball2.radius:
        # 计算碰撞法向量
        nx, ny = dx / distance, dy / distance
        
        # 计算切向量
        tx, ty = -ny, nx
        
        # 计算速度在法向和切向的分量
        v1n = ball1.vx * nx + ball1.vy * ny
        v1t = ball1.vx * tx + ball1.vy * ty
        v2n = ball2.vx * nx + ball2.vy * ny
        v2t = ball2.vx * tx + ball2.vy * ty
        
        # 计算碰撞后的法向速度 (动量守恒 + 能量损失)
        v1n_new = ((ball1.radius**3 * v1n) + (ball2.radius**3 * v2n) + 
                  ELASTICITY * ball2.radius**3 * (v2n - v1n)) / (ball1.radius**3 + ball2.radius**3)
        v2n_new = ((ball1.radius**3 * v1n) + (ball2.radius**3 * v2n) + 
                  ELASTICITY * ball1.radius**3 * (v1n - v2n)) / (ball1.radius**3 + ball2.radius**3)
        
        # 切向速度不变
        v1t_new = v1t
        v2t_new = v2t
        
        # 转换为笛卡尔速度
        ball1.vx = v1n_new * nx + v1t_new * tx
        ball1.vy = v1n_new * ny + v1t_new * ty
        ball2.vx = v2n_new * nx + v2t_new * tx
        ball2.vy = v2n_new * ny + v2t_new * ty
        
        # 分离球体，防止重叠
        overlap = (ball1.radius + ball2.radius - distance) / 2
        ball1.x -= overlap * nx
        ball1.y -= overlap * ny
        ball2.x += overlap * nx
        ball2.y += overlap * ny
        
        return True
    return False

def create_random_ball():
    """创建随机位置和速度的球"""
    angle = random.uniform(0, 2 * math.pi)
    distance = random.uniform(0, HEPTAGON_RADIUS * 0.8)
    
    x = CENTER[0] + distance * math.cos(angle)
    y = CENTER[1] + distance * math.sin(angle)
    
    speed = random.uniform(100, 300)  # 像素/秒
    angle = random.uniform(0, 2 * math.pi)
    
    vx = speed * math.cos(angle)
    vy = speed * math.sin(angle)
    
    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
    
    return Ball(x, y, vx, vy, color)

def main():
    clock = pygame.time.Clock()
    
    # 创建七边形
    heptagon = Heptagon(CENTER, HEPTAGON_RADIUS)
    
    # 创建球
    balls = [create_random_ball() for _ in range(20)]
    
    # 游戏状态
    paused = False
    running = True
    font = pygame.font.SysFont(None, 24)
    
    # 创建半透明表面用于轨迹
    trail_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    
    while running:
        dt = clock.tick(FPS) / 1000.0  # 转换为秒
        
        # 事件处理
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_SPACE:
                    paused = not paused
                elif event.key == pygame.K_r:
                    # 重置球
                    balls = [create_random_ball() for _ in range(20)]
                    trail_surface.fill((0, 0, 0, 0))  # 清除轨迹
                elif event.key == pygame.K_c:
                    # 清除轨迹
                    trail_surface.fill((0, 0, 0, 0))
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 添加新球
                if len(balls) < 50:  # 限制最大球数
                    x, y = pygame.mouse.get_pos()
                    speed = random.uniform(100, 300)
                    angle = random.uniform(0, 2 * math.pi)
                    vx = speed * math.cos(angle)
                    vy = speed * math.sin(angle)
                    color = (random.randint(50, 255), random.randint(50, 255), random.randint(50, 255))
                    balls.append(Ball(x, y, vx, vy, color))
        
        if not paused:
            # 更新七边形
            heptagon.update(dt)
            
            # 更新所有球
            for ball in balls:
                ball.update(dt)
                
                # 检查与七边形的碰撞
                heptagon.check_collision(ball)
            
            # 检查球之间的碰撞
            for i in range(len(balls)):
                for j in range(i + 1, len(balls)):
                    check_ball_collision(balls[i], balls[j])
        
        # 绘制
        screen.fill(BLACK)
        
        # 添加轨迹淡化效果
        fade_surface = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        fade_surface.fill((0, 0, 0, 25))  # 半透明黑色
        trail_surface.blit(fade_surface, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)
        
        # 绘制轨迹
        screen.blit(trail_surface, (0, 0))
        
        # 绘制七边形
        heptagon.draw(screen)
        
        # 绘制球
        for ball in balls:
            ball.draw(trail_surface)
        
        # 显示FPS和球数
        fps_text = font.render(f"FPS: {int(clock.get_fps())}", True, WHITE)
        balls_text = font.render(f"Balls: {len(balls)}", True, WHITE)
        status_text = font.render(f"Status: {'PAUSED' if paused else 'RUNNING'}", True, WHITE)
        
        screen.blit(fps_text, (10, 10))
        screen.blit(balls_text, (10, 40))
        screen.blit(status_text, (10, 70))
        
        # 显示帮助信息
        help_text = [
            "Controls:",
            "SPACE - Pause/Resume",
            "R - Reset balls",
            "C - Clear trails",
            "ESC - Quit",
            "Click - Add new ball"
        ]
        
        for i, text in enumerate(help_text):
            rendered = font.render(text, True, WHITE)
            screen.blit(rendered, (WIDTH - 200, 10 + i * 30))
        
        pygame.display.flip()
    
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()