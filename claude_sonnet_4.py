import pygame
import math
import random
import sys
from typing import List, Tuple

# 初始化Pygame
pygame.init()

# ===== 常量定义 =====
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
WINDOW_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

# 七边形参数
HEPTAGON_RADIUS = 300
HEPTAGON_SIDES = 7
ROTATION_SPEED = 15  # 度/秒

# 球体参数
BALL_COUNT = 20
BALL_RADIUS = 8
GRAVITY = 9.81 * 30  # 缩放重力以适应屏幕坐标
RESTITUTION = 0.85  # 弹性系数

# 显示参数
FPS = 60
BACKGROUND_COLOR = (0, 0, 0)
HEPTAGON_COLOR = (255, 255, 255)

class Vector2D:
    """二维向量类"""
    def __init__(self, x: float = 0, y: float = 0):
        self.x = x
        self.y = y
    
    def __add__(self, other):
        return Vector2D(self.x + other.x, self.y + other.y)
    
    def __sub__(self, other):
        return Vector2D(self.x - other.x, self.y - other.y)
    
    def __mul__(self, scalar):
        return Vector2D(self.x * scalar, self.y * scalar)
    
    def __truediv__(self, scalar):
        return Vector2D(self.x / scalar, self.y / scalar)
    
    def magnitude(self):
        return math.sqrt(self.x**2 + self.y**2)
    
    def normalize(self):
        mag = self.magnitude()
        if mag == 0:
            return Vector2D(0, 0)
        return Vector2D(self.x / mag, self.y / mag)
    
    def dot(self, other):
        return self.x * other.x + self.y * other.y
    
    def tuple(self):
        return (self.x, self.y)

class Ball:
    """球体类"""
    def __init__(self, x: float, y: float):
        self.position = Vector2D(x, y)
        self.velocity = Vector2D(
            random.uniform(-200, 200),  # 随机初始速度
            random.uniform(-200, 200)
        )
        self.radius = BALL_RADIUS
        self.color = (
            random.randint(50, 255),
            random.randint(50, 255),
            random.randint(50, 255)
        )
        self.trail = []  # 轨迹点列表
    
    def update(self, dt: float):
        """更新球的位置和速度"""
        # 应用重力
        self.velocity.y += GRAVITY * dt
        
        # 更新位置
        self.position = self.position + self.velocity * dt
        
        # 更新轨迹
        self.trail.append((int(self.position.x), int(self.position.y)))
        if len(self.trail) > 100:  # 保留最近100个点
            self.trail.pop(0)
    
    def draw(self, screen):
        """绘制球体和轨迹"""
        # 绘制轨迹
        if len(self.trail) > 1:
            for i in range(1, len(self.trail)):
                alpha = i / len(self.trail)
                color = tuple(int(c * alpha * 0.5) for c in self.color)
                pygame.draw.circle(screen, color, self.trail[i], max(1, int(self.radius * alpha * 0.5)))
        
        # 绘制球体
        pygame.draw.circle(screen, self.color, 
                         (int(self.position.x), int(self.position.y)), 
                         self.radius)
        
        # 绘制球体边缘
        pygame.draw.circle(screen, (255, 255, 255), 
                         (int(self.position.x), int(self.position.y)), 
                         self.radius, 1)

class Heptagon:
    """七边形容器类"""
    def __init__(self, center_x: float, center_y: float, radius: float):
        self.center = Vector2D(center_x, center_y)
        self.radius = radius
        self.rotation = 0.0  # 当前旋转角度（弧度）
        self.vertices = []
        self.edges = []
        self.update_vertices()
    
    def update_vertices(self):
        """更新七边形顶点坐标"""
        self.vertices = []
        for i in range(HEPTAGON_SIDES):
            angle = (2 * math.pi * i / HEPTAGON_SIDES) + self.rotation
            x = self.center.x + self.radius * math.cos(angle)
            y = self.center.y + self.radius * math.sin(angle)
            self.vertices.append(Vector2D(x, y))
        
        # 计算边的信息（起点、终点、法向量）
        self.edges = []
        for i in range(len(self.vertices)):
            start = self.vertices[i]
            end = self.vertices[(i + 1) % len(self.vertices)]
            
            # 计算边向量和法向量
            edge_vector = end - start
            normal = Vector2D(-edge_vector.y, edge_vector.x).normalize()
            
            self.edges.append({
                'start': start,
                'end': end,
                'normal': normal,
                'edge_vector': edge_vector
            })
    
    def rotate(self, dt: float):
        """旋转七边形"""
        self.rotation += math.radians(ROTATION_SPEED) * dt
        self.update_vertices()
    
    def point_inside(self, point: Vector2D) -> bool:
        """检查点是否在七边形内部"""
        for edge in self.edges:
            # 使用叉积判断点在边的哪一侧
            to_point = point - edge['start']
            if to_point.dot(edge['normal']) > 0:
                return False
        return True
    
    def get_collision_info(self, ball: Ball) -> dict:
        """获取球与七边形碰撞信息"""
        min_distance = float('inf')
        collision_edge = None
        
        for edge in self.edges:
            # 计算球心到边的距离
            to_ball = ball.position - edge['start']
            
            # 投影到边向量上
            edge_length = edge['edge_vector'].magnitude()
            if edge_length == 0:
                continue
                
            projection = to_ball.dot(edge['edge_vector']) / edge_length
            projection = max(0, min(edge_length, projection))
            
            # 最近点
            closest_point = edge['start'] + edge['edge_vector'].normalize() * projection
            distance = (ball.position - closest_point).magnitude()
            
            if distance < min_distance:
                min_distance = distance
                collision_edge = edge
        
        if min_distance <= ball.radius and collision_edge:
            return {
                'collision': True,
                'distance': min_distance,
                'normal': collision_edge['normal']
            }
        
        return {'collision': False}
    
    def draw(self, screen):
        """绘制七边形"""
        points = [(int(v.x), int(v.y)) for v in self.vertices]
        pygame.draw.polygon(screen, HEPTAGON_COLOR, points, 2)

class PhysicsSimulation:
    """物理模拟主类"""
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("旋转七边形弹跳球物理模拟")
        self.clock = pygame.time.Clock()
        
        self.heptagon = Heptagon(WINDOW_CENTER[0], WINDOW_CENTER[1], HEPTAGON_RADIUS)
        self.balls = []
        self.paused = False
        self.show_fps = True
        
        # 创建字体对象
        self.font = pygame.font.Font(None, 36)
        
        self.create_balls()
    
    def create_balls(self):
        """创建球体"""
        self.balls = []
        for _ in range(BALL_COUNT):
            # 在七边形内部随机生成位置
            while True:
                x = random.uniform(WINDOW_CENTER[0] - HEPTAGON_RADIUS + BALL_RADIUS, 
                                 WINDOW_CENTER[0] + HEPTAGON_RADIUS - BALL_RADIUS)
                y = random.uniform(WINDOW_CENTER[1] - HEPTAGON_RADIUS + BALL_RADIUS, 
                                 WINDOW_CENTER[1] + HEPTAGON_RADIUS - BALL_RADIUS)
                
                test_ball = Ball(x, y)
                if self.heptagon.point_inside(test_ball.position):
                    # 检查与其他球的距离
                    valid = True
                    for existing_ball in self.balls:
                        distance = (test_ball.position - existing_ball.position).magnitude()
                        if distance < (test_ball.radius + existing_ball.radius) * 1.5:
                            valid = False
                            break
                    
                    if valid:
                        self.balls.append(test_ball)
                        break
    
    def handle_ball_collision(self, ball1: Ball, ball2: Ball):
        """处理球与球之间的碰撞"""
        distance_vector = ball2.position - ball1.position
        distance = distance_vector.magnitude()
        
        if distance < ball1.radius + ball2.radius and distance > 0:
            # 归一化碰撞向量
            collision_normal = distance_vector.normalize()
            
            # 分离球体
            overlap = ball1.radius + ball2.radius - distance
            separation = collision_normal * (overlap / 2)
            ball1.position = ball1.position - separation
            ball2.position = ball2.position + separation
            
            # 计算相对速度
            relative_velocity = ball1.velocity - ball2.velocity
            velocity_along_normal = relative_velocity.dot(collision_normal)
            
            # 如果球体正在分离，不处理碰撞
            if velocity_along_normal > 0:
                return
            
            # 计算碰撞冲量
            restitution = RESTITUTION
            impulse_magnitude = -(1 + restitution) * velocity_along_normal / 2
            impulse = collision_normal * impulse_magnitude
            
            # 应用冲量
            ball1.velocity = ball1.velocity + impulse
            ball2.velocity = ball2.velocity - impulse
    
    def handle_boundary_collision(self, ball: Ball):
        """处理球与边界的碰撞"""
        collision_info = self.heptagon.get_collision_info(ball)
        
        if collision_info['collision']:
            normal = collision_info['normal']
            
            # 将球推出边界
            overlap = ball.radius - collision_info['distance']
            ball.position = ball.position + normal * overlap
            
            # 反射速度
            velocity_along_normal = ball.velocity.dot(normal)
            if velocity_along_normal < 0:
                ball.velocity = ball.velocity - normal * (2 * velocity_along_normal * RESTITUTION)
    
    def update(self, dt: float):
        """更新模拟状态"""
        if self.paused:
            return
        
        # 旋转七边形
        self.heptagon.rotate(dt)
        
        # 更新球的位置
        for ball in self.balls:
            ball.update(dt)
        
        # 处理碰撞
        for ball in self.balls:
            self.handle_boundary_collision(ball)
        
        # 处理球与球之间的碰撞
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                self.handle_ball_collision(self.balls[i], self.balls[j])
    
    def draw(self):
        """绘制所有元素"""
        self.screen.fill(BACKGROUND_COLOR)
        
        # 绘制七边形
        self.heptagon.draw(self.screen)
        
        # 绘制球体
        for ball in self.balls:
            ball.draw(self.screen)
        
        # 绘制FPS
        if self.show_fps:
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, (255, 255, 255))
            self.screen.blit(fps_text, (10, 10))
        
        # 绘制控制提示
        if self.paused:
            pause_text = self.font.render("PAUSED - Press SPACE to resume", True, (255, 255, 0))
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, 50))
            self.screen.blit(pause_text, text_rect)
        
        controls_text = [
            "Controls:",
            "SPACE - Pause/Resume",
            "R - Reset balls",
            "ESC - Exit"
        ]
        
        for i, text in enumerate(controls_text):
            rendered_text = pygame.font.Font(None, 24).render(text, True, (200, 200, 200))
            self.screen.blit(rendered_text, (10, WINDOW_HEIGHT - 100 + i * 20))
        
        pygame.display.flip()
    
    def handle_events(self):
        """处理事件"""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return False
                elif event.key == pygame.K_SPACE:
                    self.paused = not self.paused
                elif event.key == pygame.K_r:
                    self.create_balls()
                elif event.key == pygame.K_f:
                    self.show_fps = not self.show_fps
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                # 鼠标点击添加新球
                if event.button == 1:  # 左键
                    mouse_pos = pygame.mouse.get_pos()
                    new_ball = Ball(mouse_pos[0], mouse_pos[1])
                    if self.heptagon.point_inside(new_ball.position):
                        self.balls.append(new_ball)
        
        return True
    
    def run(self):
        """主循环"""
        print("=== 旋转七边形弹跳球物理模拟 ===")
        print("控制说明:")
        print("- 空格键: 暂停/恢复")
        print("- R键: 重置球的位置")
        print("- F键: 显示/隐藏FPS")
        print("- 鼠标左键: 在点击位置添加新球")
        print("- ESC键: 退出程序")
        print("=" * 40)
        
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0  # 转换为秒
            
            running = self.handle_events()
            self.update(dt)
            self.draw()
        
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    # 检查pygame是否正确安装
    try:
        simulation = PhysicsSimulation()
        simulation.run()
    except ImportError as e:
        print("错误: 需要安装pygame库")
        print("请运行: pip install pygame")
        sys.exit(1)
    except Exception as e:
        print(f"运行时错误: {e}")
        sys.exit(1)