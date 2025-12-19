"""
正七边形弹跳球物理模拟程序
============================
功能：
- 正七边形容器以恒定速度顺时针旋转
- 20个弹跳球在容器内运动
- 完整的物理模拟（重力、碰撞、能量损失）
- 交互控制（暂停、重置、添加球）

作者：Claude
日期：2024
"""

import pygame
import math
import random
import numpy as np
from dataclasses import dataclass
from typing import List, Tuple
from collections import deque

# ==================== 常量定义 ====================
# 窗口设置
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60

# 七边形设置
HEPTAGON_SIDES = 7
HEPTAGON_RADIUS = 300
HEPTAGON_CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)
ROTATION_SPEED = 15  # 度/秒（顺时针为正）

# 球体设置
BALL_RADIUS = 8
NUM_BALLS = 20
BALL_COLORS = None  # 将在运行时随机生成

# 物理设置
GRAVITY = 981  # 像素/秒² (9.81 m/s² * 100 像素/米)
RESTITUTION = 0.85  # 弹性系数
FRICTION = 0.99  # 轻微摩擦以增加稳定性

# 轨迹设置
TRAIL_LENGTH = 100  # 轨迹历史帧数

# 颜色定义
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
HEPTAGON_COLOR = (0, 200, 255)


def generate_random_color() -> Tuple[int, int, int]:
    """生成随机鲜艳颜色"""
    # 使用HSV转RGB确保颜色鲜艳
    h = random.random()
    s = 0.7 + random.random() * 0.3  # 70-100% 饱和度
    v = 0.7 + random.random() * 0.3  # 70-100% 明度
    
    # HSV to RGB 转换
    i = int(h * 6)
    f = h * 6 - i
    p = v * (1 - s)
    q = v * (1 - f * s)
    t = v * (1 - (1 - f) * s)
    
    if i % 6 == 0:
        r, g, b = v, t, p
    elif i % 6 == 1:
        r, g, b = q, v, p
    elif i % 6 == 2:
        r, g, b = p, v, t
    elif i % 6 == 3:
        r, g, b = p, q, v
    elif i % 6 == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    
    return (int(r * 255), int(g * 255), int(b * 255))


@dataclass
class Ball:
    """球体类，包含位置、速度和属性"""
    x: float
    y: float
    vx: float
    vy: float
    radius: float
    color: Tuple[int, int, int]
    mass: float = 1.0
    spin: float = 0.0  # 自旋角速度（弧度/秒）
    angle: float = 0.0  # 当前旋转角度
    trail: deque = None  # 轨迹历史
    
    def __post_init__(self):
        if self.trail is None:
            self.trail = deque(maxlen=TRAIL_LENGTH)
    
    def update_trail(self):
        """更新轨迹"""
        self.trail.append((self.x, self.y))
    
    def update_spin(self, dt: float):
        """更新自旋角度"""
        self.angle += self.spin * dt


class Heptagon:
    """正七边形类，处理旋转和碰撞检测"""
    
    def __init__(self, center: Tuple[float, float], radius: float, sides: int = 7):
        self.center = np.array(center, dtype=float)
        self.radius = radius
        self.sides = sides
        self.angle = 0.0  # 当前旋转角度（弧度）
        self.vertices = self._calculate_vertices()
    
    def _calculate_vertices(self) -> np.ndarray:
        """计算七边形顶点（相对于当前角度）"""
        vertices = []
        for i in range(self.sides):
            # 从顶部开始，顺时针方向
            theta = self.angle + 2 * math.pi * i / self.sides - math.pi / 2
            x = self.center[0] + self.radius * math.cos(theta)
            y = self.center[1] + self.radius * math.sin(theta)
            vertices.append([x, y])
        return np.array(vertices)
    
    def rotate(self, delta_angle: float):
        """旋转七边形"""
        self.angle += delta_angle
        self.vertices = self._calculate_vertices()
    
    def get_edges(self) -> List[Tuple[np.ndarray, np.ndarray]]:
        """获取所有边（起点，终点）"""
        edges = []
        for i in range(self.sides):
            start = self.vertices[i]
            end = self.vertices[(i + 1) % self.sides]
            edges.append((start, end))
        return edges
    
    def get_edge_normal(self, edge_start: np.ndarray, edge_end: np.ndarray) -> np.ndarray:
        """计算边的内法向量（指向内部）"""
        edge = edge_end - edge_start
        # 法向量（垂直于边）
        normal = np.array([-edge[1], edge[0]])
        normal = normal / np.linalg.norm(normal)
        
        # 确保法向量指向内部（朝向中心）
        edge_center = (edge_start + edge_end) / 2
        to_center = self.center - edge_center
        if np.dot(normal, to_center) < 0:
            normal = -normal
        
        return normal
    
    def point_to_edge_distance(self, point: np.ndarray, edge_start: np.ndarray, 
                                edge_end: np.ndarray) -> Tuple[float, np.ndarray]:
        """
        计算点到边的距离和最近点
        返回：(距离, 最近点)
        """
        edge = edge_end - edge_start
        edge_length_sq = np.dot(edge, edge)
        
        if edge_length_sq == 0:
            return np.linalg.norm(point - edge_start), edge_start
        
        # 参数 t 表示最近点在边上的位置 (0-1)
        t = max(0, min(1, np.dot(point - edge_start, edge) / edge_length_sq))
        closest_point = edge_start + t * edge
        distance = np.linalg.norm(point - closest_point)
        
        return distance, closest_point
    
    def is_point_inside(self, point: np.ndarray) -> bool:
        """检查点是否在七边形内部"""
        for edge_start, edge_end in self.get_edges():
            normal = self.get_edge_normal(edge_start, edge_end)
            edge_center = (edge_start + edge_end) / 2
            to_point = point - edge_center
            if np.dot(to_point, normal) < 0:
                return False
        return True
    
    def get_wall_velocity_at_point(self, point: np.ndarray, angular_velocity: float) -> np.ndarray:
        """
        计算墙壁在某点的线速度（由于旋转）
        angular_velocity: 角速度（弧度/秒）
        """
        r = point - self.center
        # 线速度 = ω × r (在2D中)
        # v_x = -ω * r_y, v_y = ω * r_x
        return np.array([-angular_velocity * r[1], angular_velocity * r[0]])


class PhysicsEngine:
    """物理引擎，处理所有物理计算"""
    
    def __init__(self, heptagon: Heptagon):
        self.heptagon = heptagon
        self.angular_velocity = math.radians(ROTATION_SPEED)  # 转换为弧度/秒
    
    def apply_gravity(self, ball: Ball, dt: float):
        """应用重力"""
        ball.vy += GRAVITY * dt
    
    def apply_friction(self, ball: Ball):
        """应用轻微摩擦"""
        ball.vx *= FRICTION
        ball.vy *= FRICTION
    
    def update_ball_position(self, ball: Ball, dt: float):
        """更新球的位置"""
        ball.x += ball.vx * dt
        ball.y += ball.vy * dt
    
    def check_wall_collision(self, ball: Ball) -> bool:
        """
        检测并处理球与墙壁的碰撞
        返回：是否发生碰撞
        """
        ball_pos = np.array([ball.x, ball.y])
        collision_occurred = False
        
        for edge_start, edge_end in self.heptagon.get_edges():
            distance, closest_point = self.heptagon.point_to_edge_distance(
                ball_pos, edge_start, edge_end
            )
            
            if distance < ball.radius:
                collision_occurred = True
                
                # 获取碰撞法向量（指向内部）
                normal = self.heptagon.get_edge_normal(edge_start, edge_end)
                
                # 将球推出墙壁
                penetration = ball.radius - distance
                ball.x += normal[0] * penetration
                ball.y += normal[1] * penetration
                
                # 计算墙壁在碰撞点的速度
                wall_velocity = self.heptagon.get_wall_velocity_at_point(
                    closest_point, self.angular_velocity
                )
                
                # 计算相对速度
                ball_velocity = np.array([ball.vx, ball.vy])
                relative_velocity = ball_velocity - wall_velocity
                
                # 计算法向速度分量
                normal_velocity = np.dot(relative_velocity, normal)
                
                # 只有当球正在靠近墙壁时才反弹
                if normal_velocity < 0:
                    # 反弹：反转法向速度分量，应用弹性系数
                    ball_velocity -= (1 + RESTITUTION) * normal_velocity * normal
                    
                    # 添加墙壁运动的影响
                    ball.vx = ball_velocity[0]
                    ball.vy = ball_velocity[1]
                    
                    # 更新球的自旋（基于切向速度）
                    tangent = np.array([normal[1], -normal[0]])
                    tangent_velocity = np.dot(relative_velocity, tangent)
                    ball.spin += tangent_velocity * 0.1 / ball.radius
        
        return collision_occurred
    
    def check_ball_collision(self, ball1: Ball, ball2: Ball) -> bool:
        """
        检测并处理两个球之间的碰撞
        使用动量守恒和能量损失
        """
        dx = ball2.x - ball1.x
        dy = ball2.y - ball1.y
        distance = math.sqrt(dx * dx + dy * dy)
        
        min_distance = ball1.radius + ball2.radius
        
        if distance < min_distance and distance > 0:
            # 碰撞法向量
            nx = dx / distance
            ny = dy / distance
            
            # 分离球（避免重叠）
            overlap = min_distance - distance
            ball1.x -= nx * overlap / 2
            ball1.y -= ny * overlap / 2
            ball2.x += nx * overlap / 2
            ball2.y += ny * overlap / 2
            
            # 相对速度
            dvx = ball1.vx - ball2.vx
            dvy = ball1.vy - ball2.vy
            
            # 相对速度在碰撞法向上的分量
            dvn = dvx * nx + dvy * ny
            
            # 只有当球正在靠近时才处理碰撞
            if dvn > 0:
                # 使用动量守恒和能量损失计算冲量
                m1, m2 = ball1.mass, ball2.mass
                impulse = (1 + RESTITUTION) * dvn / (1/m1 + 1/m2)
                
                # 应用冲量
                ball1.vx -= impulse * nx / m1
                ball1.vy -= impulse * ny / m1
                ball2.vx += impulse * nx / m2
                ball2.vy += impulse * ny / m2
                
                # 交换部分自旋
                avg_spin = (ball1.spin + ball2.spin) / 2
                ball1.spin = ball1.spin * 0.8 + avg_spin * 0.2
                ball2.spin = ball2.spin * 0.8 + avg_spin * 0.2
                
                return True
        
        return False


class Simulation:
    """主模拟类，管理整个程序"""
    
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("正七边形弹跳球物理模拟 - 按空格暂停 | R重置 | 点击添加球 | ESC退出")
        
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
        
        # 创建七边形
        self.heptagon = Heptagon(HEPTAGON_CENTER, HEPTAGON_RADIUS, HEPTAGON_SIDES)
        
        # 创建物理引擎
        self.physics = PhysicsEngine(self.heptagon)
        
        # 创建球
        self.balls: List[Ball] = []
        self.initialize_balls()
        
        # 状态变量
        self.running = True
        self.paused = False
        self.show_trails = True
        self.show_spin = True
        
        # 性能监控
        self.fps_history = deque(maxlen=60)
    
    def initialize_balls(self):
        """初始化所有球"""
        self.balls.clear()
        for _ in range(NUM_BALLS):
            ball = self.create_random_ball()
            self.balls.append(ball)
    
    def create_random_ball(self, x: float = None, y: float = None) -> Ball:
        """创建一个随机位置和速度的球"""
        if x is None or y is None:
            # 在七边形内随机生成位置
            max_attempts = 100
            for _ in range(max_attempts):
                # 在以中心为原点的圆内随机生成
                angle = random.uniform(0, 2 * math.pi)
                r = random.uniform(0, HEPTAGON_RADIUS * 0.7)  # 0.7确保在内部
                x = HEPTAGON_CENTER[0] + r * math.cos(angle)
                y = HEPTAGON_CENTER[1] + r * math.sin(angle)
                
                # 检查是否在七边形内
                if self.heptagon.is_point_inside(np.array([x, y])):
                    break
        
        # 随机速度
        speed = random.uniform(50, 200)
        angle = random.uniform(0, 2 * math.pi)
        vx = speed * math.cos(angle)
        vy = speed * math.sin(angle)
        
        # 随机颜色
        color = generate_random_color()
        
        # 随机自旋
        spin = random.uniform(-5, 5)
        
        return Ball(
            x=x, y=y,
            vx=vx, vy=vy,
            radius=BALL_RADIUS,
            color=color,
            mass=1.0,
            spin=spin,
            angle=random.uniform(0, 2 * math.pi)
        )
    
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
                    self.initialize_balls()
                    self.heptagon.angle = 0
                    self.heptagon.vertices = self.heptagon._calculate_vertices()
                elif event.key == pygame.K_t:
                    self.show_trails = not self.show_trails
                elif event.key == pygame.K_s:
                    self.show_spin = not self.show_spin
            
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:  # 左键
                    mouse_pos = pygame.mouse.get_pos()
                    # 检查点击位置是否在七边形内
                    if self.heptagon.is_point_inside(np.array(mouse_pos)):
                        new_ball = self.create_random_ball(mouse_pos[0], mouse_pos[1])
                        self.balls.append(new_ball)
    
    def update(self, dt: float):
        """更新物理状态"""
        if self.paused:
            return
        
        # 旋转七边形（顺时针为正角度）
        rotation_delta = math.radians(ROTATION_SPEED) * dt
        self.heptagon.rotate(rotation_delta)
        
        # 更新每个球
        for ball in self.balls:
            # 应用重力
            self.physics.apply_gravity(ball, dt)
            
            # 更新位置
            self.physics.update_ball_position(ball, dt)
            
            # 应用轻微摩擦
            self.physics.apply_friction(ball)
            
            # 检测墙壁碰撞
            self.physics.check_wall_collision(ball)
            
            # 更新自旋
            ball.update_spin(dt)
            
            # 更新轨迹
            ball.update_trail()
        
        # 检测球与球之间的碰撞
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                self.physics.check_ball_collision(self.balls[i], self.balls[j])
    
    def draw_trail(self, ball: Ball):
        """绘制球的轨迹"""
        if len(ball.trail) < 2:
            return
        
        points = list(ball.trail)
        for i in range(len(points) - 1):
            # 透明度随时间衰减
            alpha = int(255 * (i / len(points)) * 0.5)
            color = (*ball.color[:3], alpha)
            
            # 创建带透明度的surface
            start = points[i]
            end = points[i + 1]
            
            # 简化绘制：直接画线，颜色渐变
            fade_color = tuple(int(c * (i / len(points))) for c in ball.color)
            pygame.draw.line(self.screen, fade_color, start, end, 1)
    
    def draw_ball_with_spin(self, ball: Ball):
        """绘制带自旋效果的球"""
        # 绘制球体
        pygame.draw.circle(self.screen, ball.color, (int(ball.x), int(ball.y)), ball.radius)
        
        if self.show_spin:
            # 绘制自旋指示线
            line_length = ball.radius * 0.7
            end_x = ball.x + line_length * math.cos(ball.angle)
            end_y = ball.y + line_length * math.sin(ball.angle)
            
            # 高亮颜色
            highlight = tuple(min(255, c + 100) for c in ball.color)
            pygame.draw.line(self.screen, highlight, 
                           (int(ball.x), int(ball.y)), 
                           (int(end_x), int(end_y)), 2)
        
        # 绘制边缘高光
        pygame.draw.circle(self.screen, WHITE, (int(ball.x), int(ball.y)), ball.radius, 1)
    
    def draw(self):
        """绘制所有内容"""
        # 清屏
        self.screen.fill(BLACK)
        
        # 绘制七边形
        vertices = [(int(v[0]), int(v[1])) for v in self.heptagon.vertices]
        pygame.draw.polygon(self.screen, HEPTAGON_COLOR, vertices, 3)
        
        # 绘制七边形顶点
        for v in vertices:
            pygame.draw.circle(self.screen, WHITE, v, 5)
        
        # 绘制中心点
        pygame.draw.circle(self.screen, GRAY, HEPTAGON_CENTER, 5)
        
        # 绘制轨迹
        if self.show_trails:
            for ball in self.balls:
                self.draw_trail(ball)
        
        # 绘制球
        for ball in self.balls:
            self.draw_ball_with_spin(ball)
        
        # 绘制UI信息
        self.draw_ui()
        
        pygame.display.flip()
    
    def draw_ui(self):
        """绘制用户界面信息"""
        # FPS显示
        current_fps = self.clock.get_fps()
        self.fps_history.append(current_fps)
        avg_fps = sum(self.fps_history) / len(self.fps_history)
        
        fps_text = self.font.render(f"FPS: {avg_fps:.1f}", True, WHITE)
        self.screen.blit(fps_text, (10, 10))
        
        # 球数量
        ball_text = self.font.render(f"Balls: {len(self.balls)}", True, WHITE)
        self.screen.blit(ball_text, (10, 45))
        
        # 旋转角度
        angle_deg = math.degrees(self.heptagon.angle) % 360
        angle_text = self.font.render(f"Rotation: {angle_deg:.1f}°", True, WHITE)
        self.screen.blit(angle_text, (10, 80))
        
        # 暂停状态
        if self.paused:
            pause_text = self.font.render("PAUSED", True, (255, 255, 0))
            text_rect = pause_text.get_rect(center=(WINDOW_WIDTH // 2, 50))
            self.screen.blit(pause_text, text_rect)
        
        # 控制说明
        controls = [
            "Controls:",
            "SPACE - Pause/Resume",
            "R - Reset balls",
            "T - Toggle trails",
            "S - Toggle spin",
            "Click - Add ball",
            "ESC - Exit"
        ]
        
        y_offset = WINDOW_HEIGHT - len(controls) * 20 - 10
        for i, text in enumerate(controls):
            control_text = self.small_font.render(text, True, GRAY)
            self.screen.blit(control_text, (10, y_offset + i * 20))
    
    def run(self):
        """主循环"""
        while self.running:
            # 计算时间步长
            dt = self.clock.tick(FPS) / 1000.0
            
            # 限制dt以防止物理爆炸
            dt = min(dt, 1/30)
            
            # 处理事件
            self.handle_events()
            
            # 更新物理
            self.update(dt)
            
            # 绘制
            self.draw()
        
        pygame.quit()


def main():
    """程序入口"""
    print("=" * 50)
    print("正七边形弹跳球物理模拟")
    print("=" * 50)
    print("\n控制说明:")
    print("  SPACE  - 暂停/恢复模拟")
    print("  R      - 重置所有球")
    print("  T      - 显示/隐藏轨迹")
    print("  S      - 显示/隐藏自旋效果")
    print("  鼠标点击 - 添加新球")
    print("  ESC    - 退出程序")
    print("\n" + "=" * 50)
    
    simulation = Simulation()
    simulation.run()


if __name__ == "__main__":
    main()