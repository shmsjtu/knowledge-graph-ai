# relation_utils.py
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Tuple, Dict, Any
import new_Lib.new_prompt as prompt
from .api_utils import ask_deepseek
from .parse_utils import convert_string_to_list


def batch_extract_relations(
    entities_1_list: List[str],
    entities_2_list: List[str],
    text_1: str,
    text_2: str,
    relation_name: str,
    api_key: str,
    api_endpoint: str,
    batch_num: int,
    existing_relations: List[Tuple[str, str, Dict[str, str]]],
    all_new_relations: List[Tuple[str, str, Dict[str, str]]],
    max_workers: int = 4
) -> None:
    """
    批量提取关系（多线程并发版本）

    参数:
        entities_1_list: 第一个实体列表
        entities_2_list: 第二个实体列表
        text_1: 第一个文本
        text_2: 第二个文本
        relation_name: 关系名称（用于日志）
        api_key: API 密钥
        api_endpoint: API 端点
        batch_num: 批次数量
        existing_relations: 已有关系列表（用于去重）
        all_new_relations: 新提取的关系列表（会被修改）
        max_workers: 最大并发线程数，默认为 4
    """
    if not entities_1_list:
        return

    entities_1_shuffled = entities_1_list.copy()
    random.shuffle(entities_1_shuffled)

    batch_size = max(1, len(entities_1_shuffled) // batch_num)
    batches = [
        entities_1_shuffled[i:i + batch_size]
        for i in range(0, len(entities_1_shuffled), batch_size)
    ]

    print(f"  开始提取 {relation_name} 关系，共 {len(entities_1_shuffled)} 个实体，"
          f"batch_size={batch_size}，并发线程数={min(max_workers, len(batches))}")

    lock = threading.Lock()

    def process_one_batch(batch_idx: int, batch: List[str]) -> List:
        """处理单个批次，返回去重后的新关系列表"""
        batch_str = '\n'.join(batch)
        entities_2_minus_batch = [e for e in entities_2_list if e not in batch]
        entities_2_str = '\n'.join(entities_2_minus_batch) if entities_2_minus_batch else ""

        print(f"    [{relation_name}] 批次 {batch_idx + 1}/{len(batches)}，"
              f"包含 {len(batch)} 个实体...")

        messages = prompt.build_prompt_relation(
            entities_1=batch_str,
            entities_2=entities_2_str,
            text_1=text_1,
            text_2=text_2
        )
        raw_response = ask_deepseek(messages, api_key, api_endpoint, modell="chat")
        batch_relations = convert_string_to_list(raw_response)

        valid_relations = []
        for relation in batch_relations:
            if relation[0] == relation[1]:
                continue
            valid_relations.append(relation)

        print(f"    [{relation_name}] 批次 {batch_idx + 1} 提取到 {len(valid_relations)} 个关系")
        return valid_relations

    with ThreadPoolExecutor(max_workers=min(max_workers, len(batches))) as executor:
        futures = {
            executor.submit(process_one_batch, idx, batch): idx
            for idx, batch in enumerate(batches)
        }
        for future in as_completed(futures):
            try:
                batch_relations = future.result()
            except Exception as e:
                print(f"    [{relation_name}] 某批次处理异常: {e}")
                continue

            new_added = 0
            with lock:
                for relation in batch_relations:
                    relation_key = (relation[0], relation[1])
                    is_duplicate = any(
                        (r[0], r[1]) == relation_key
                        for r in existing_relations + all_new_relations
                    )
                    if not is_duplicate:
                        all_new_relations.append(relation)
                        new_added += 1

            print(f"    [{relation_name}] 本批次新增 {new_added} 条关系（去重后）")

    print(f"  [{relation_name}] 全部批次完成，累计新增关系数: {len(all_new_relations)}")
