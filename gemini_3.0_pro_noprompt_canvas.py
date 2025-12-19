import pygame
import math
import random

# --- 配置参数 ---
WINDOW_WIDTH = 800
WINDOW_HEIGHT = 800
FPS = 60

# 颜色定义 (R, G, B)
BLACK = (10, 10, 10)
WHITE = (240, 240, 240)
GRAY = (100, 100, 100)
RED = (255, 60, 60)
GREEN = (60, 255, 60)
BLUE = (60, 60, 255)

# 物理参数
HEPTAGON_RADIUS = 300
BALL_RADIUS = 8
BALL_COUNT_INITIAL = 20
GRAVITY = 0.25           # 重力加速度 (像素/帧^2)，调整以获得良好的视觉效果
RESTITUTION = 0.85       # 弹性系数 (能量保留比率)
FRICTION = 0.99          # 空气阻力/摩擦 (防止球永远乱飞)
ROTATION_SPEED = 15      # 度/秒

# 屏幕中心
CENTER = (WINDOW_WIDTH // 2, WINDOW_HEIGHT // 2)

class Ball:
    def __init__(self, x, y):
        self.pos = pygame.math.Vector2(x, y)
        # 随机初始速度
        self.vel = pygame.math.Vector2(random.uniform(-4, 4), random.uniform(-4, 4))
        self.radius = BALL_RADIUS
        # 随机颜色
        self.color = (random.randint(100, 255), random.randint(100, 255), random.randint(100, 255))
        # 轨迹 (保存最近100个位置)
        self.trail = []
        self.max_trail = 100
        
    def update(self):
        # 保存轨迹
        self.trail.append((int(self.pos.x), int(self.pos.y)))
        if len(self.trail) > self.max_trail:
            self.trail.pop(0)
            
        # 应用重力
        self.vel.y += GRAVITY
        # 应用空气阻力
        self.vel *= FRICTION
        # 更新位置
        self.pos += self.vel

    def draw(self, surface):
        # 绘制轨迹
        if len(self.trail) > 1:
            pygame.draw.lines(surface, self.color, False, self.trail, 1)
        # 绘制球体
        pygame.draw.circle(surface, self.color, (int(self.pos.x), int(self.pos.y)), self.radius)

class Simulation:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT))
        pygame.display.set_caption("旋转七边形物理模拟 - [R]重置 [Space]暂停 [Click]加球")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("consolas", 18)
        
        self.running = True
        self.paused = False
        
        self.rotation_angle = 0.0 # 当前旋转角度 (弧度)
        self.rotation_speed_rad = math.radians(ROTATION_SPEED) / FPS # 每帧旋转弧度
        
        self.balls = []
        self.reset_balls()

    def reset_balls(self):
        self.balls = []
        for _ in range(BALL_COUNT_INITIAL):
            self.add_ball_randomly()

    def add_ball_randomly(self):
        # 在中心附近随机生成球，避免一开始就在墙外
        angle = random.uniform(0, math.pi * 2)
        dist = random.uniform(0, HEPTAGON_RADIUS * 0.5)
        x = CENTER[0] + math.cos(angle) * dist
        y = CENTER[1] + math.sin(angle) * dist
        self.balls.append(Ball(x, y))

    def get_heptagon_vertices(self):
        """计算当前旋转状态下的七边形顶点"""
        vertices = []
        sides = 7
        for i in range(sides):
            # 顺时针旋转，所以加上 rotation_angle
            angle = self.rotation_angle + (2 * math.pi * i / sides)
            x = CENTER[0] + HEPTAGON_RADIUS * math.cos(angle)
            y = CENTER[1] + HEPTAGON_RADIUS * math.sin(angle)
            vertices.append(pygame.math.Vector2(x, y))
        return vertices

    def resolve_ball_ball_collisions(self):
        """处理球与球之间的碰撞"""
        for i in range(len(self.balls)):
            for j in range(i + 1, len(self.balls)):
                b1 = self.balls[i]
                b2 = self.balls[j]
                
                delta = b1.pos - b2.pos
                dist_sq = delta.length_squared()
                min_dist = b1.radius + b2.radius
                
                if dist_sq < min_dist * min_dist:
                    dist = math.sqrt(dist_sq)
                    if dist == 0: continue # 避免除零错误
                    
                    # 碰撞法线
                    n = delta / dist
                    
                    # 1. 位置修正 (防止重叠)
                    overlap = min_dist - dist
                    correction = n * (overlap * 0.5)
                    b1.pos += correction
                    b2.pos -= correction
                    
                    # 2. 速度响应 (动量守恒，假设质量相等)
                    # 相对速度
                    rel_vel = b1.vel - b2.vel
                    vel_along_normal = rel_vel.dot(n)
                    
                    # 如果球正在分离，则不处理
                    if vel_along_normal > 0:
                        continue
                        
                    # 计算冲量 j
                    j = -(1 + RESTITUTION) * vel_along_normal
                    j /= 2 # 1/m1 + 1/m2, 假设 m=1
                    
                    impulse = j * n
                    b1.vel += impulse
                    b2.vel -= impulse

    def resolve_wall_collisions(self, vertices):
        """处理球与旋转墙壁的碰撞"""
        # 墙壁的角速度 (标量)
        omega = self.rotation_speed_rad * FPS # rad/s
        
        for ball in self.balls:
            # 优化：如果球离中心太远，大概率出界了，先做个粗略检查
            if (ball.pos - pygame.math.Vector2(CENTER)).length() > HEPTAGON_RADIUS + ball.radius:
                # 简单地把球拉回来 (防止极端情况下穿墙飞出屏幕)
                to_center = (pygame.math.Vector2(CENTER) - ball.pos).normalize()
                ball.vel += to_center * 0.5
            
            # 检查每一面墙
            num_verts = len(vertices)
            for i in range(num_verts):
                p1 = vertices[i]
                p2 = vertices[(i + 1) % num_verts]
                
                # 墙向量
                wall_vec = p2 - p1
                # 墙法线 (指向内部)
                # 假设顶点是顺时针生成的，(-y, x) 指向左侧（即内部，如果坐标系Y向下且顶点顺时针）
                # 这里需要根据顶点生成顺序仔细判断
                # 我们的顶点生成是顺时针，屏幕坐标Y向下。
                # 向量 P1->P2. 法线指向中心。
                normal = pygame.math.Vector2(-wall_vec.y, wall_vec.x).normalize()
                
                # 确保法线指向七边形中心
                to_center = pygame.math.Vector2(CENTER) - p1
                if normal.dot(to_center) < 0:
                    normal = -normal
                
                # 计算球心到墙线的距离
                # 投影公式: dot(ball_pos - p1, normal)
                rel_pos = ball.pos - p1
                dist = rel_pos.dot(normal)
                
                # 碰撞检测 (由于我们在容器内部，dist > 0 表示在内部。
                # 当 dist < radius 时，球接触墙壁)
                # 注意：如果多边形完全包含中心，且法线指向中心，那么内部点的 dist 是正的。
                # 我们需要找到距离最小的那面墙（实际上是距离变为负数或者小于半径）
                
                # 这里我们简化逻辑：如果球穿过了墙平面（dist < radius），就反弹
                # 为了防止球被后面的墙误判，我们只处理 dist < radius 且 dist > -radius (在墙附近)
                
                if dist < ball.radius:
                    # --- 碰撞发生 ---
                    
                    # 1. 墙壁在该点的线速度
                    # V_wall = omega x r
                    # 在2D中，切向速度方向垂直于半径
                    r_vec = ball.pos - pygame.math.Vector2(CENTER)
                    # 顺时针旋转的切向速度向量
                    wall_vel = pygame.math.Vector2(-r_vec.y, r_vec.x) * self.rotation_speed_rad
                    
                    # 2. 相对速度
                    v_rel = ball.vel - wall_vel
                    
                    # 3. 只有当球正在接近墙壁时才反弹
                    vel_normal = v_rel.dot(normal)
                    if vel_normal < 0:
                        # 反弹速度
                        v_rel_new = v_rel - (1 + RESTITUTION) * vel_normal * normal
                        
                        # 转换回绝对速度
                        ball.vel = v_rel_new + wall_vel
                        
                        # 4. 位置修正 (防止陷入墙内)
                        overlap = ball.radius - dist
                        ball.pos += normal * overlap

    def run(self):
        while self.running:
            # --- 事件处理 ---
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    elif event.key == pygame.K_SPACE:
                        self.paused = not self.paused
                    elif event.key == pygame.K_r:
                        self.reset_balls()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1: # 左键点击
                        mx, my = pygame.mouse.get_pos()
                        self.balls.append(Ball(mx, my))

            # --- 更新逻辑 ---
            if not self.paused:
                # 更新七边形旋转
                self.rotation_angle += self.rotation_speed_rad
                
                # 获取当前顶点
                vertices = self.get_heptagon_vertices()
                
                # 物理子步 (Sub-stepping) 可以增加精度，但这里简化为单步
                # 1. 更新球位置
                for ball in self.balls:
                    ball.update()
                
                # 2. 碰撞检测
                self.resolve_ball_ball_collisions()
                self.resolve_wall_collisions(vertices)

            # --- 渲染绘制 ---
            self.screen.fill(BLACK)
            
            # 获取绘制用的顶点 (如果暂停，也需要画出当前的)
            vertices = self.get_heptagon_vertices()
            
            # 1. 绘制容器
            # 绘制填充的半透明背景 (可选)
            # pygame.gfxdraw 不支持填充多边形很好，这里只画线框
            pygame.draw.polygon(self.screen, WHITE, vertices, 3)
            
            # 2. 绘制球
            for ball in self.balls:
                ball.draw(self.screen)
            
            # 3. 绘制 UI 信息
            fps_text = self.font.render(f"FPS: {int(self.clock.get_fps())}", True, GREEN)
            count_text = self.font.render(f"Balls: {len(self.balls)}", True, GREEN)
            info_text = self.font.render("Space:Pause R:Reset Click:Add Ball", True, GRAY)
            
            self.screen.blit(fps_text, (10, 10))
            self.screen.blit(count_text, (10, 30))
            self.screen.blit(info_text, (10, WINDOW_HEIGHT - 30))

            if self.paused:
                pause_text = self.font.render("PAUSED", True, RED)
                text_rect = pause_text.get_rect(center=CENTER)
                self.screen.blit(pause_text, text_rect)

            pygame.display.flip()
            self.clock.tick(FPS)

        pygame.quit()

if __name__ == "__main__":
    sim = Simulation()
    sim.run()