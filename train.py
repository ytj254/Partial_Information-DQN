import time
import datetime

from utils import *
from EnvMultiDiscrete import SumoEnv

from DoubleDQN import DoubleDQN
from stable_baselines3 import DQN, PPO
from stable_baselines3.common.env_util import make_vec_env
from stable_baselines3.common.vec_env import VecNormalize, SubprocVecEnv, DummyVecEnv, VecMonitor
from stable_baselines3.common.utils import get_linear_fn
from FeaturesExtractor import CustomCNN, CustomCombinedExtractor, SaveOnBestTrainingRewardCallback


def learn(obs_type, cv=False):
    start_time = time.time()

    alg = 'PPO'
    models_dir = create_folder(folders_name='models', alg=alg)
    log_dir = create_folder(folders_name='logs', alg=alg)

    sumo_cmd = set_sumo()
    gamma = 0.65
    lr = get_linear_fn(0.001, 0.0001, 0.5)
    n_envs = 8
    train_freq = 400

    env = make_vec_env(
        SumoEnv,
        n_envs=n_envs,
        vec_env_cls=SubprocVecEnv,
        env_kwargs=dict(
            sumo_cmd=sumo_cmd,
            obs_type=obs_type,
            cv_only=cv,
        ),
    )
    env = VecNormalize(env, gamma=gamma)
    env = VecMonitor(env, log_dir)

    if alg == 'PPO':
        hyperparams = {
            "learning_rate": lr,
            "n_steps": 512,
            "batch_size": 256,
            "n_epochs": 3,
            "gamma": gamma,
            # "gae_lambda": 0.95,
            "clip_range": 0.2,
            "max_grad_norm": 0.5,
            "ent_coef": 0.01,
            # "clip_range_vf": None,
            "vf_coef": 0.5,
        }
    else:
        hyperparams = {
            "learning_rate": 0.0001,
            "buffer_size": 50000,
            "learning_starts": 500,
            "batch_size": 32,
            "gamma": gamma,
            "train_freq": 400,
            "gradient_steps": 100,
            "target_update_interval": 200,
            "exploration_fraction": 0.2,
            "exploration_initial_eps": 1.0,
            "exploration_final_eps": 0.01,
        }

    if obs_type == 'vec':
        model = PPO(
            'MlpPolicy', env,
            **hyperparams,
            stats_window_size=10,
            verbose=0,
            tensorboard_log=log_dir,
        )

    else:
        policy_type = 'CnnPolicy'
        features_extractor = CustomCNN

        if obs_type == 'comb':
            policy_type = 'MultiInputPolicy'
            features_extractor = CustomCombinedExtractor

        policy_kwargs = dict(
            features_extractor_class=features_extractor,
            features_extractor_kwargs=dict(features_dim=128),
            # share_features_extractor=False,
            # net_arch=dict(pi=[32, 32], vf=[64, 64]),
            # activation_fn=th.nn.ReLU,
            normalize_images=False,
        )

        model = PPO(
            policy_type, env,
            **hyperparams,
            policy_kwargs=policy_kwargs,
            stats_window_size=10,
            verbose=1,
            tensorboard_log=log_dir,
        )

    # print(model.policy)

    # check_freq = 1000
    # callback = SaveOnBestTrainingRewardCallback(
    #     check_freq=int(check_freq / n_envs),
    #     log_dir=log_dir,
    #     save_path=models_dir,
    # )

    time_steps = int(4e5)

    model.learn(
        total_timesteps=time_steps,
        # callback=callback,
        reset_num_timesteps=False,
        tb_log_name=alg
    )
    save_path = os.path.join(models_dir, 'final_model')
    model.save(save_path)
    stats_path = os.path.join(models_dir, 'vec_normalize.pkl')
    env.save(stats_path)
    print(f'Training time: {datetime.timedelta(seconds=int(time.time() - start_time))}')


if __name__ == '__main__':
    learn(obs_type='img', cv=True)
